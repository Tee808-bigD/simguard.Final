import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.fraud_alert import ActionTaken, FraudAlert
from ..models.transaction import Transaction, TransactionStatus
from ..schemas.transaction import TransactionCreate, TransactionResponse
from ..services.ai_engine import analyze_fraud_risk
from ..services.camara import camara_service
from ..services.fraud_detector import compute_risk_score, determine_alert_type
from ..websocket import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transactions"])
settings = get_settings()


def _risk_level_from_score(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 51:
        return "high"
    if score >= 26:
        return "medium"
    return "low"


def _result_source(camara_results: dict, ai_result: dict) -> str:
    if ai_result.get("source") == "claude_ai":
        return "live_ai"
    signal_sources = {
        value.get("source")
        for value in camara_results.values()
        if isinstance(value, dict) and value.get("source")
    }
    if "camara" in signal_sources and "simulation" in signal_sources:
        return "hybrid"
    if "camara" in signal_sources:
        return "camara"
    return "simulation"


def serialize_transaction(txn: Transaction, risk_level: str | None = None, ai_result: dict | None = None) -> dict:
    computed_risk_level = risk_level or _risk_level_from_score(txn.risk_score or 0)
    computed_ai = ai_result or {
        "primary_reason": txn.ai_explanation,
        "recommended_actions": [],
        "confidence": min((txn.risk_score or 0) + 20, 95),
        "fraud_pattern": None,
        "source": "history",
    }
    return {
        "id": txn.id,
        "phone_number": txn.phone_number,
        "amount": txn.amount,
        "currency": txn.currency,
        "transaction_type": txn.transaction_type,
        "recipient": txn.recipient,
        "status": txn.status,
        "risk_score": txn.risk_score,
        "risk_level": computed_risk_level,
        "ai_decision": txn.ai_decision,
        "ai_explanation": txn.ai_explanation,
        "primary_reason": computed_ai.get("primary_reason"),
        "recommended_actions": computed_ai.get("recommended_actions", []),
        "confidence": computed_ai.get("confidence"),
        "fraud_pattern": computed_ai.get("fraud_pattern"),
        "source": _result_source(txn.camara_results or {}, computed_ai),
        "integration_mode": settings.integration_mode,
        "camara_results": txn.camara_results,
        "created_at": txn.created_at,
    }


async def process_transaction(
    payload: TransactionCreate,
    db: Session,
):
    camara_results = camara_service.full_check(payload.phone_number, expected_phone_number=payload.phone_number)
    risk_score, risk_level, reasons = compute_risk_score(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        recipient=payload.recipient,
        camara_results=camara_results,
    )
    ai_result = analyze_fraud_risk(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type.value,
        recipient=payload.recipient,
        camara_results=camara_results,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
    )

    decision = ai_result.get("decision", "FLAG_FOR_REVIEW")
    status_map = {
        "BLOCK": TransactionStatus.BLOCKED,
        "APPROVE": TransactionStatus.APPROVED,
        "FLAG_FOR_REVIEW": TransactionStatus.FLAGGED,
    }
    status = status_map.get(decision, TransactionStatus.FLAGGED)

    txn = Transaction(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type,
        recipient=payload.recipient,
        status=status,
        risk_score=risk_score,
        ai_decision=decision,
        ai_explanation=ai_result.get("detailed_explanation"),
        camara_results=camara_results,
    )
    db.add(txn)
    db.flush()

    if risk_score >= 26 or status in (TransactionStatus.BLOCKED, TransactionStatus.FLAGGED):
        action_map = {
            TransactionStatus.BLOCKED: ActionTaken.BLOCKED,
            TransactionStatus.FLAGGED: ActionTaken.FLAGGED,
            TransactionStatus.APPROVED: ActionTaken.APPROVED,
        }
        alert = FraudAlert(
            transaction_id=txn.id,
            phone_number=payload.phone_number,
            alert_type=determine_alert_type(camara_results),
            risk_level=risk_level,
            risk_score=risk_score,
            camara_checks=camara_results,
            ai_analysis=ai_result,
            action_taken=action_map.get(status, ActionTaken.FLAGGED),
            explanation=ai_result.get("primary_reason"),
        )
        db.add(alert)

    db.commit()
    db.refresh(txn)

    response_payload = serialize_transaction(txn, risk_level=risk_level, ai_result=ai_result)
    await ws_manager.broadcast({"type": "transaction", "data": response_payload})
    return response_payload


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    return await process_transaction(payload=payload, db=db)


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    phone: Optional[str] = Query(default=None),
):
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    if phone:
        if not re.match(r"^\+[1-9]\d{6,14}$", phone):
            raise HTTPException(status_code=400, detail="Invalid phone format")
        query = query.filter(Transaction.phone_number == phone)
    rows = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    return [serialize_transaction(txn) for txn in rows]


@router.get("/{txn_id}", response_model=TransactionResponse)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_transaction(txn)

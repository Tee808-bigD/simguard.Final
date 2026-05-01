import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.fraud_alert import FraudAlert
from ..schemas.fraud_alert import FraudAlertResponse
from ..services.ai_engine import analyze_fraud_risk
from ..services.camara import camara_service
from ..services.fraud_detector import compute_risk_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fraud", tags=["fraud"])
settings = get_settings()

PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class QuickCheckRequest(BaseModel):
    phone_number: str = Field(..., max_length=20)
    amount: float = Field(default=0.0, ge=0, le=10_000_000)
    currency: str = Field(default="KES", max_length=5)
    recipient: Optional[str] = Field(default=None, max_length=100)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not PHONE_RE.match(value):
            raise ValueError("Phone must be E.164 format, e.g. +254712345678")
        return value


@router.post("/check")
async def quick_fraud_check(payload: QuickCheckRequest):
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
        transaction_type="check",
        recipient=payload.recipient,
        camara_results=camara_results,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
    )
    return {
        "phone_number": payload.phone_number,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "source": ai_result.get("source", "rule_based_fallback"),
        "integration_mode": settings.integration_mode,
        "decision": ai_result.get("decision"),
        "reasons": reasons,
        "camara_results": camara_results,
        "ai_decision": ai_result.get("decision"),
        "primary_reason": ai_result.get("primary_reason"),
        "detailed_explanation": ai_result.get("detailed_explanation"),
        "recommended_actions": ai_result.get("recommended_actions", []),
        "fraud_pattern": ai_result.get("fraud_pattern"),
        "confidence": ai_result.get("confidence"),
    }


@router.get("/alerts", response_model=list[FraudAlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    risk_level: Optional[str] = Query(default=None),
):
    query = db.query(FraudAlert)
    if risk_level:
        query = query.filter(FraudAlert.risk_level == risk_level)
    return query.order_by(FraudAlert.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/alerts/{alert_id}", response_model=FraudAlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

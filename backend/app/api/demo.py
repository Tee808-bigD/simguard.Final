import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models.fraud_alert import FraudAlert
from ..models.transaction import Transaction, TransactionType
from ..schemas.transaction import TransactionCreate
from ..services.demo_scenarios import get_demo_scenario, list_demo_scenarios
from ..websocket import ws_manager
from .transactions import process_transaction

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenarios")
def scenarios():
    return {"scenarios": list_demo_scenarios()}


@router.post("/reset")
async def reset_demo(db: Session = Depends(get_db)):
    db.query(FraudAlert).delete()
    db.query(Transaction).delete()
    db.commit()
    await ws_manager.broadcast({"type": "dashboard_reset", "data": {"status": "ok"}})
    return {"status": "reset"}


@router.post("/run-scenario/{scenario_id}")
async def run_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scenario = get_demo_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    payload = TransactionCreate(
        phone_number=scenario["payload"]["phone_number"],
        amount=scenario["payload"]["amount"],
        currency=scenario["payload"]["currency"],
        transaction_type=TransactionType(scenario["payload"]["transaction_type"]),
        recipient=scenario["payload"].get("recipient"),
        agent_id=scenario["payload"].get("agent_id"),
    )
    return await process_transaction(payload=payload, db=db)


@router.post("/showcase")
async def run_showcase(db: Session = Depends(get_db)):
    sequence = list_demo_scenarios()

    async def _playback():
        background_db = SessionLocal()
        try:
            for scenario in sequence:
                payload = TransactionCreate(
                    phone_number=scenario["payload"]["phone_number"],
                    amount=scenario["payload"]["amount"],
                    currency=scenario["payload"]["currency"],
                    transaction_type=TransactionType(scenario["payload"]["transaction_type"]),
                    recipient=scenario["payload"].get("recipient"),
                    agent_id=scenario["payload"].get("agent_id"),
                )
                await process_transaction(payload=payload, db=background_db)
                await asyncio.sleep(1.2)
        finally:
            background_db.close()

    asyncio.create_task(_playback())
    return {"status": "started", "sequence": [item["id"] for item in sequence]}

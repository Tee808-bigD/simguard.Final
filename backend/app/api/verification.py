import re

from fastapi import APIRouter, HTTPException, Path

from ..config import get_settings
from ..services.ai_engine import analyze_fraud_risk
from ..services.camara import camara_service
from ..services.fraud_detector import compute_risk_score

router = APIRouter(prefix="/api/verification", tags=["verification"])
settings = get_settings()
PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def _validate_phone(phone: str) -> str:
    value = phone.strip()
    if not PHONE_RE.match(value):
        raise HTTPException(status_code=400, detail="Invalid phone number format. Use E.164, e.g. +254712345678")
    return value


def _summary(phone: str, results: dict) -> dict:
    risk_score, risk_level, reasons = compute_risk_score(
        phone_number=phone,
        amount=0,
        currency="KES",
        recipient=None,
        camara_results=results,
    )
    ai_result = analyze_fraud_risk(
        phone_number=phone,
        amount=0,
        currency="KES",
        transaction_type="verification",
        recipient=None,
        camara_results=results,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
    )
    return {
        "phone_number": phone,
        "source": ai_result.get("source", "rule_based_fallback"),
        "integration_mode": settings.integration_mode,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "decision": ai_result.get("decision"),
        "primary_reason": ai_result.get("primary_reason"),
        "recommended_actions": ai_result.get("recommended_actions", []),
        "results": results,
    }


@router.get("/sim-status/{phone_number}")
def check_sim_status(phone_number: str = Path(..., max_length=20)):
    phone = _validate_phone(phone_number)
    return _summary(phone, {
        "sim_swap_24h": camara_service.check_sim_swap(phone, max_age_hours=24),
        "sim_swap_7d": camara_service.check_sim_swap(phone, max_age_hours=168),
        "device_swap": camara_service.empty_signal("device_swap", max_age_hours=240),
        "number_verification": camara_service.check_number_verification(phone, phone),
    })


@router.get("/device-status/{phone_number}")
def check_device_status(phone_number: str = Path(..., max_length=20)):
    phone = _validate_phone(phone_number)
    return _summary(phone, {
        "sim_swap_24h": camara_service.empty_signal("sim_swap", max_age_hours=24),
        "sim_swap_7d": camara_service.empty_signal("sim_swap", max_age_hours=168),
        "device_swap": camara_service.check_device_swap(phone, max_age_hours=240),
        "number_verification": camara_service.check_number_verification(phone, phone),
    })


@router.get("/full-check/{phone_number}")
def full_check(phone_number: str = Path(..., max_length=20)):
    phone = _validate_phone(phone_number)
    return _summary(phone, camara_service.full_check(phone, expected_phone_number=phone))

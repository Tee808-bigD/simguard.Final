import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..models.transaction import TransactionStatus, TransactionType

PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")

SUPPORTED_CURRENCIES = {
    "KES", "UGX", "TZS", "ZMW", "GHS", "NGN", "ZAR",
    "USD", "EUR", "GBP", "MWK", "MZN", "RWF", "ETB",
    "XOF", "XAF", "AOA", "MAD", "EGP",
}


class TransactionCreate(BaseModel):
    phone_number: str = Field(..., max_length=20)
    amount: float = Field(..., gt=0, le=10_000_000)
    currency: str = Field(default="KES", max_length=5)
    transaction_type: TransactionType
    recipient: Optional[str] = Field(default=None, max_length=100)
    agent_id: Optional[str] = Field(default=None, max_length=50)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        value = value.strip()
        if not PHONE_RE.match(value):
            raise ValueError("Phone must be E.164 format, e.g. +254712345678")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency. Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}")
        return value

    @field_validator("recipient")
    @classmethod
    def sanitize_recipient(cls, value: Optional[str]) -> Optional[str]:
        if value:
            value = re.sub(r"<[^>]+>", "", value).strip()
        return value or None


class TransactionResponse(BaseModel):
    id: int
    phone_number: str
    amount: float
    currency: str
    transaction_type: TransactionType
    recipient: Optional[str]
    status: TransactionStatus
    risk_score: int
    risk_level: Optional[str] = None
    ai_decision: Optional[str]
    ai_explanation: Optional[str]
    primary_reason: Optional[str] = None
    recommended_actions: list[str] = []
    confidence: Optional[int] = None
    fraud_pattern: Optional[str] = None
    source: Optional[str] = None
    integration_mode: Optional[str] = None
    camara_results: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}

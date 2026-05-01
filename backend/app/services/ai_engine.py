import json
import logging
from typing import Optional

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are SimGuard AI, an expert fraud detection system specializing in
SIM swap fraud prevention for African mobile money networks.

Always respond in valid JSON with this exact structure:
{
  "decision": "BLOCK" | "APPROVE" | "FLAG_FOR_REVIEW",
  "confidence": 0-100,
  "primary_reason": "one-sentence summary for the agent",
  "detailed_explanation": "2-3 sentence explanation suitable for a mobile money agent",
  "recommended_actions": ["action1", "action2"],
  "fraud_pattern": "sim_swap_drain" | "device_takeover" | "high_value_suspicious" | "normal" | "coordinated_attack"
}
"""


def analyze_fraud_risk(
    phone_number: str,
    amount: float,
    currency: str,
    transaction_type: str,
    recipient: Optional[str],
    camara_results: dict,
    risk_score: int,
    risk_level: str,
    reasons: list[str],
) -> dict:
    if settings.integration_mode == "SIMULATION":
        return _rule_based_fallback(risk_score, risk_level, reasons, camara_results)

    if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("sk-ant-your"):
        logger.warning("ANTHROPIC_API_KEY not configured - using deterministic fallback")
        return _rule_based_fallback(risk_score, risk_level, reasons, camara_results)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        user_message = f"""Analyze this mobile money transaction for fraud:

TRANSACTION:
- Phone: {phone_number}
- Amount: {amount} {currency}
- Type: {transaction_type}
- Recipient: {recipient or 'N/A'}

CAMARA API RESULTS:
{json.dumps(camara_results, indent=2)}

RULE-BASED SCORING:
- Risk score: {risk_score}/100
- Risk level: {risk_level}
- Detected signals: {chr(10).join(f'  - {reason}' for reason in reasons) if reasons else '  - None'}
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        required = {"decision", "confidence", "primary_reason", "detailed_explanation", "recommended_actions", "fraud_pattern"}
        if not required.issubset(result):
            raise ValueError("Incomplete AI response")
        result["source"] = "claude_ai"
        return result
    except Exception as exc:
        logger.warning(f"Claude analysis failed, using deterministic fallback: {exc}")
        return _rule_based_fallback(risk_score, risk_level, reasons, camara_results)


def _rule_based_fallback(risk_score: int, risk_level: str, reasons: list[str], camara_results: dict) -> dict:
    sim_24h = camara_results.get("sim_swap_24h", {}).get("swapped", False)
    device_swap = camara_results.get("device_swap", {}).get("swapped", False)

    if risk_score >= 60 or sim_24h:
        decision = "BLOCK"
        primary = "Block this transaction immediately due to active fraud indicators."
        actions = [
            "Do not process the transaction.",
            "Ask the customer to complete in-person verification.",
            "Escalate to the fraud operations team.",
        ]
        pattern = "coordinated_attack" if device_swap else "sim_swap_drain"
    elif risk_score >= 30:
        decision = "FLAG_FOR_REVIEW"
        primary = "Pause and perform additional customer verification before proceeding."
        actions = [
            "Check a second form of customer identity.",
            "Confirm the transaction on an alternate channel.",
            "Proceed only after manual confirmation.",
        ]
        pattern = "device_takeover" if device_swap else "high_value_suspicious"
    else:
        decision = "APPROVE"
        primary = "No significant telecom fraud indicators were detected."
        actions = ["Proceed with the transaction."]
        pattern = "normal"

    return {
        "decision": decision,
        "confidence": min(risk_score + 20, 95),
        "primary_reason": primary,
        "detailed_explanation": f"Risk score: {risk_score}/100 ({risk_level}). "
        + (f"Signals: {'; '.join(reasons[:3])}" if reasons else "No telecom risk signals were raised."),
        "recommended_actions": actions,
        "fraud_pattern": pattern,
        "source": "rule_based_fallback",
    }

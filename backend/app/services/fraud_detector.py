import logging

logger = logging.getLogger(__name__)

RISK_LEVELS = {
    "low": (0, 25),
    "medium": (26, 50),
    "high": (51, 74),
    "critical": (75, 100),
}


def compute_risk_score(
    phone_number: str,
    amount: float,
    currency: str,
    recipient: str | None,
    camara_results: dict,
) -> tuple[int, str, list[str]]:
    score = 0
    reasons = []

    sim_24h = camara_results.get("sim_swap_24h", {})
    sim_7d = camara_results.get("sim_swap_7d", {})
    device = camara_results.get("device_swap", {})
    number_verification = camara_results.get("number_verification", {})

    if sim_24h.get("swapped"):
        score += 60
        reasons.append("SIM swap detected within the last 24 hours")
    elif sim_7d.get("swapped"):
        score += 40
        reasons.append("SIM swap detected within the last 7 days")

    if device.get("swapped"):
        score += 30
        reasons.append("Device swap detected on this subscriber line")

    if number_verification.get("matched") is False:
        score += 25
        reasons.append("Number verification mismatch for the active handset")

    usd_rates = {
        "KES": 0.0077, "UGX": 0.00027, "TZS": 0.00039, "ZMW": 0.056,
        "GHS": 0.062, "NGN": 0.00063, "ZAR": 0.055, "USD": 1.0,
        "EUR": 1.09, "GBP": 1.27, "MWK": 0.00058, "MZN": 0.016,
        "RWF": 0.00073, "ETB": 0.018, "XOF": 0.0017, "XAF": 0.0017,
        "AOA": 0.0011, "MAD": 0.10, "EGP": 0.020,
    }
    usd_amount = amount * usd_rates.get(currency.upper(), 1.0)

    if usd_amount > 1000:
        score += 30
        reasons.append(f"Very high transaction value (~${usd_amount:,.0f} USD)")
    elif usd_amount > 500:
        score += 20
        reasons.append(f"High transaction value (~${usd_amount:,.0f} USD)")
    elif usd_amount > 200:
        score += 10
        reasons.append(f"Above-average transaction value (~${usd_amount:,.0f} USD)")

    if sim_24h.get("swapped") and usd_amount > 200:
        score += 25
        reasons.append("Composite pattern: recent SIM swap plus high-value transfer")

    if (sim_24h.get("swapped") or sim_7d.get("swapped")) and recipient:
        score += 20
        reasons.append("Composite pattern: swap signal plus transfer to a recipient")

    if sim_24h.get("swapped") and device.get("swapped"):
        score += 15
        reasons.append("Composite pattern: SIM and device swap together")

    if number_verification.get("matched") is False and usd_amount > 200:
        score += 10
        reasons.append("Composite pattern: unverified number with meaningful value")

    score = min(score, 100)

    risk_level = "low"
    for level, (lo, hi) in RISK_LEVELS.items():
        if lo <= score <= hi:
            risk_level = level
            break

    return score, risk_level, reasons


def determine_alert_type(camara_results: dict) -> str:
    sim_24h = camara_results.get("sim_swap_24h", {}).get("swapped", False)
    sim_7d = camara_results.get("sim_swap_7d", {}).get("swapped", False)
    device = camara_results.get("device_swap", {}).get("swapped", False)
    number_mismatch = camara_results.get("number_verification", {}).get("matched") is False

    flags = sum([bool(sim_24h or sim_7d), bool(device), bool(number_mismatch)])
    if flags >= 2:
        return "composite"
    if sim_24h or sim_7d:
        return "sim_swap"
    if device:
        return "device_swap"
    if number_mismatch:
        return "number_mismatch"
    return "high_value"

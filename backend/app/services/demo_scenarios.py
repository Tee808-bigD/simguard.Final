from copy import deepcopy


DEMO_SCENARIOS = [
    {
        "id": "block_sim_swap",
        "title": "Salary Day SIM Swap Drain",
        "decision": "BLOCK",
        "summary": "Recent SIM swap and high-value transfer shortly after a number takeover.",
        "payload": {
            "phone_number": "+99999991000",
            "amount": 18500,
            "currency": "KES",
            "transaction_type": "send",
            "recipient": "New wallet beneficiary",
            "agent_id": "AGENT-KE-102",
        },
    },
    {
        "id": "flag_device_takeover",
        "title": "Device Change Before Cash-out",
        "decision": "FLAG_FOR_REVIEW",
        "summary": "Device swap and medium-value withdrawal that needs manual confirmation.",
        "payload": {
            "phone_number": "+99999991002",
            "amount": 6200,
            "currency": "KES",
            "transaction_type": "withdraw",
            "recipient": "Cash pickup",
            "agent_id": "AGENT-KE-204",
        },
    },
    {
        "id": "approve_verified_customer",
        "title": "Trusted Returning Customer",
        "decision": "APPROVE",
        "summary": "No telecom fraud indicators and clean number verification.",
        "payload": {
            "phone_number": "+99999991001",
            "amount": 950,
            "currency": "KES",
            "transaction_type": "send",
            "recipient": "School fees merchant",
            "agent_id": "AGENT-KE-305",
        },
    },
]


def list_demo_scenarios() -> list[dict]:
    return [deepcopy(item) for item in DEMO_SCENARIOS]


def get_demo_scenario(scenario_id: str) -> dict | None:
    for scenario in DEMO_SCENARIOS:
        if scenario["id"] == scenario_id:
            return deepcopy(scenario)
    return None

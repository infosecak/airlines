"""Deterministic output guardrails for the SkyBridge demo.

This action is intentionally simple and auditable: it scans the generated bot
message before delivery and blocks it when it contains demo-sensitive markers
or common sensitive-data patterns. The KB values are synthetic and exist only
to demonstrate output-rail enforcement.
"""

import re
from typing import Optional

from nemoguardrails.actions import action


# All values used by the demo are synthetic. Patterns are deliberately narrow
# enough to avoid turning this teaching example into a generic DLP product.
SENSITIVE_OUTPUT_PATTERNS = [
    ("demo secret/token", re.compile(r"\b(?:SB-DEMO-(?:TOKEN|SECRET|KEY)-[A-Z0-9-]{4,}|sb_demo_[a-z0-9_]{6,})\b", re.I)),
    ("internal routing code", re.compile(r"\bSB-(?:FIN-REFUND|LOY-MILES|BAG-CLAIM)-L\d\b", re.I)),
    ("demo customer id", re.compile(r"\bDEMO-CUST-\d{4,}\b", re.I)),
    ("demo employee pin", re.compile(r"\bSB-PIN-\d{6}\b", re.I)),
    ("demo payment token", re.compile(r"\btok_demo_[a-z0-9_]{4,}\b", re.I)),
    ("test email address", re.compile(r"\b[A-Z0-9._%+-]+@(?:example\.test|skybridge-demo\.test)\b", re.I)),
    ("US SSN-like value", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("16-digit payment-card-like value", re.compile(r"\b(?:\d[ -]?){15}\d\b")),
    ("demo passport", re.compile(r"\bP-DEMO-\d{7}\b", re.I)),
]


@action(is_system_action=True)
async def detect_sensitive_output(context: Optional[dict] = None):
    """Return True when the generated response contains demo-sensitive data.

    In a NeMo output rail, ``bot_message`` is the generated response currently
    being evaluated. ``bot_response`` is kept as a compatibility fallback for
    older configurations/examples.
    """
    context = context or {}
    bot_message = context.get("bot_message") or context.get("bot_response") or ""

    for _label, pattern in SENSITIVE_OUTPUT_PATTERNS:
        if pattern.search(bot_message):
            return True

    return False

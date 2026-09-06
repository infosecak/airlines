"""NeMo execution tracing for the SkyBridge demo.

The trace deliberately separates runtime evidence (what NeMo actually reports)
from explanatory UI metadata. We never invent confidence scores or claim that
NIST itself made a blocking decision.
"""
from nist_mapping import RAIL_NIST_MAP

PIPELINE_STAGES = [
    {"rail_name": None, "label": "User Input", "kind": "input"},
    {"rail_name": "self check input", "label": "Input Guardrail", "kind": "rail"},
    {"rail_name": None, "label": "Generate Answer", "kind": "generation"},
    {"rail_name": "self check output", "label": "Output Guardrail", "kind": "rail"},
    {"rail_name": "self check facts", "label": "Fact Check", "kind": "rail"},
]


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _friendly_reason(rail_name: str, blocked: bool) -> str:
    if not blocked:
        return "Control executed and allowed processing to continue."
    return {
        "self check input": "The request did not satisfy the assistant's input policy, so NeMo stopped the turn before answer generation.",
        "self check output": "The generated response did not satisfy the output policy, so NeMo stopped it before delivery to the user.",
        "self check facts": "The generated response did not satisfy the grounding/factuality control, so NeMo stopped it before delivery.",
    }.get(rail_name, "A NeMo rail stopped processing according to the configured policy.")


def run_guarded_with_trace(rails, user_input: str):
    response = rails.generate(
        messages=[{"role": "user", "content": user_input}],
        options={"log": {"activated_rails": True}},
    )

    resp_field = _get(response, "response", response)
    if isinstance(resp_field, list) and resp_field:
        answer = _get(resp_field[0], "content", str(resp_field[0]))
    else:
        answer = resp_field

    log = _get(response, "log", None)
    activated = _get(log, "activated_rails", []) if log is not None else []

    rails_by_name = {}
    activation_order = []
    for rail in activated:
        name = _get(rail, "name")
        if name:
            blocked = bool(_get(rail, "stop", False))
            rails_by_name[name] = blocked
            activation_order.append((name, blocked))

    trace = []
    for name, blocked in activation_order:
        mapping = RAIL_NIST_MAP.get(name)
        if mapping:
            trace.append({
                "name": name,
                "blocked": blocked,
                "status": "blocked" if blocked else "executed",
                "runtime_reason": _friendly_reason(name, blocked),
                **mapping,
            })

    pipeline = []
    halted = False
    for stage in PIPELINE_STAGES:
        kind = stage["kind"]
        if kind == "input":
            pipeline.append({"label": stage["label"], "status": "received", "detail": "Request received by the application."})
            continue
        if halted:
            pipeline.append({"label": stage["label"], "status": "skipped", "detail": "Not executed because an earlier guardrail stopped the turn."})
            continue
        if kind == "generation":
            pipeline.append({"label": stage["label"], "status": "executed", "detail": "Answer generation was reached."})
            continue

        name = stage["rail_name"]
        if name in rails_by_name:
            blocked = rails_by_name[name]
            pipeline.append({
                "label": stage["label"],
                "status": "blocked" if blocked else "executed",
                "detail": _friendly_reason(name, blocked),
                "rail_name": name,
            })
            if blocked:
                halted = True
        else:
            pipeline.append({"label": stage["label"], "status": "skipped", "detail": "This stage was not reported as activated for this turn.", "rail_name": name})

    blocked_rail = next((x for x in trace if x["blocked"]), None)
    event = {
        "blocked": blocked_rail is not None,
        "blocked_at": blocked_rail["name"] if blocked_rail else None,
        "decision": "BLOCK" if blocked_rail else "ALLOW",
        "reason": blocked_rail["runtime_reason"] if blocked_rail else "All reported NeMo controls allowed the turn to continue.",
        "nist": blocked_rail.get("event_mapping") if blocked_rail else None,
    }
    return answer, trace, pipeline, event

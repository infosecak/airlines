"""NIST AI RMF mappings used to explain guardrail evidence.

NIST AI RMF is a governance/risk-management framework; NeMo Guardrails is the
runtime enforcement mechanism. These mappings describe relevance/evidence and
must not be presented as NIST certification or as NIST making the block.
"""

_INPUT_EVENT = {
    "summary": "Runtime input-policy enforcement provides evidence that the system is operating within its defined use context and that identified misuse/scope risks are being treated.",
    "functions": {
        "GOVERN": {"practice": "Policy & accountability", "applies": "The assistant has an explicit, reviewable boundary for permitted use. The NeMo input policy operationalizes that boundary at runtime.", "evidence": "A named input rail executed and produced a recorded allow/block decision."},
        "MAP": {"practice": "Context & intended use", "applies": "The event is evaluated against SkyBridge's intended customer-support context rather than allowing unrestricted model use.", "evidence": "The blocked turn demonstrates enforcement of the application's defined operating scope."},
        "MEASURE": {"practice": "MEASURE 2.7 — security/resilience evaluation", "applies": "The input control evaluates incoming requests for policy-relevant misuse and adversarial or out-of-scope behavior.", "evidence": "NeMo reported self check input as activated and stopped processing for this turn."},
        "MANAGE": {"practice": "Risk response & treatment", "applies": "The system responds to the detected policy condition by preventing downstream generation instead of merely logging it.", "evidence": "Generation and subsequent controls are skipped after the blocking decision."},
    },
}

_OUTPUT_EVENT = {
    "summary": "Runtime output-policy enforcement provides evidence that generated content is checked before release and policy failures are actively treated.",
    "functions": {
        "GOVERN": {"practice": "Policy & accountability", "applies": "Output requirements are encoded as reviewable controls rather than relying only on model behavior.", "evidence": "A named output rail executed and produced a recorded decision."},
        "MAP": {"practice": "Impact & misuse context", "applies": "Potential harms from releasing policy-violating content are considered in the deployment context.", "evidence": "The generated answer reached an output control before user delivery."},
        "MEASURE": {"practice": "MEASURE 2.6 — safety evaluation", "applies": "The output is evaluated for configured failure modes and misuse scenarios.", "evidence": "NeMo reported self check output as activated and stopped the turn."},
        "MANAGE": {"practice": "Risk response & treatment", "applies": "A failing generated response is withheld rather than exposed to the user.", "evidence": "The output blocking decision prevents delivery and downstream processing."},
    },
}

_FACT_EVENT = {
    "summary": "Grounding/factuality enforcement provides evidence that model responses are checked against reliability expectations before release.",
    "functions": {
        "GOVERN": {"practice": "Trustworthiness policy", "applies": "The application defines grounding as an expected property of customer-support answers.", "evidence": "A dedicated factuality rail is configured and observable."},
        "MAP": {"practice": "Context & consequences", "applies": "Incorrect airline policy information is treated as a deployment-specific risk.", "evidence": "The answer is evaluated in the context of trusted SkyBridge policy information."},
        "MEASURE": {"practice": "MEASURE 2.5 — validity & reliability", "applies": "The control evaluates whether the response meets configured grounding/reliability expectations.", "evidence": "NeMo reported self check facts as activated and stopped the turn."},
        "MANAGE": {"practice": "Risk response & treatment", "applies": "A response that fails the grounding control is prevented from reaching the user.", "evidence": "The factuality decision is used as an active runtime mitigation."},
    },
}

_SENSITIVE_OUTPUT_EVENT = {
    "summary": "A deterministic NeMo output rail detected sensitive-looking data in generated content and withheld the response before it reached the user.",
    "functions": {
        "GOVERN": {"practice": "Data-handling policy & accountability", "applies": "The application encodes an explicit rule that customer records, payment details, credentials, and internal-only values must not be released in model output.", "evidence": "A named custom NeMo output rail executed using a reviewable Python pattern set."},
        "MAP": {"practice": "Information exposure risk", "applies": "Knowledge-base retrieval can place sensitive material in model context even when the user's question is legitimate, creating a data-leakage risk at the output boundary.", "evidence": "This turn reached answer generation and was evaluated before release."},
        "MEASURE": {"practice": "MEASURE 2.6 — safety evaluation", "applies": "The generated response is tested for configured sensitive-data failure modes using deterministic checks in addition to the LLM-based output policy.", "evidence": "NeMo reported the sensitive data output rail as activated and stopped the turn."},
        "MANAGE": {"practice": "Risk response & treatment", "applies": "A response that matches the sensitive-data policy is withheld and replaced with a safe refusal rather than being delivered.", "evidence": "The blocking output rail prevented later output/fact stages and prevented release of the generated text."},
    },
}

RAIL_NIST_MAP = {
    "sensitive data output": {"category": "MEASURE 2.6", "label": "Sensitive-data output filtering", "nist_text": "Evaluate output safety and information-exposure failure modes before release.", "description": "Runs a deterministic Python output filter inside NeMo to detect demo customer data, payment details, credentials, and internal-only tokens.", "event_mapping": _SENSITIVE_OUTPUT_EVENT},
    "self check input": {"category": "MEASURE 2.7", "label": "Input policy / security & resilience", "nist_text": "Evaluate relevant security, resilience, misuse, and adversarial risks using appropriate testing and evidence.", "description": "Evaluates incoming messages against the configured NeMo input policy before generation.", "event_mapping": _INPUT_EVENT},
    "self check output": {"category": "MEASURE 2.6", "label": "Output safety evaluation", "nist_text": "Evaluate safety-relevant failure modes, hazards, and misuse scenarios.", "description": "Evaluates generated responses against configured output policy before delivery.", "event_mapping": _OUTPUT_EVENT},
    "self check facts": {"category": "MEASURE 2.5", "label": "Validity & reliability", "nist_text": "Evaluate validity, reliability, and accuracy using evidence appropriate to the deployment context.", "description": "Evaluates whether generated responses meet the application's grounding expectations.", "event_mapping": _FACT_EVENT},
}

NIST_FUNCTIONS = {
    "GOVERN": {"description": "Establish policies, accountability, roles, and risk-management processes.", "coverage": ["The demo defines explicit runtime policies and makes guardrail decisions observable."]},
    "MAP": {"description": "Establish context, intended use, affected parties, and relevant AI risks.", "coverage": ["SkyBridge scopes the assistant to airline customer-support use and models misuse/out-of-scope behavior as a deployment risk."]},
    "MEASURE": {"description": "Assess and track identified risks using tests, metrics, and evidence.", "coverage": ["Input, deterministic sensitive-data output, LLM-based output-policy, and grounding rails produce per-turn runtime evidence; the red-team suite provides repeatable evaluation evidence."]},
    "MANAGE": {"description": "Prioritize and treat risks, then monitor the effectiveness of responses.", "coverage": ["Blocking rails actively stop unsafe or non-compliant processing, while regression tests can be re-run after changes."]},
}

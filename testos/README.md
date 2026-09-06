# SkyBridge Airlines Assistant — Guardrails A/B Demo (macOS)

A small, real (not simulated) RAG chatbot for demonstrating the difference
between an unguarded and a NeMo Guardrails–protected LLM assistant.

**Design principle:** the SAME model (`gpt-3.5-turbo`) and the SAME source
documents power both paths. The only variable that changes is whether
NeMo Guardrails wraps the model — that's what makes the comparison a fair
test of guardrails, not just "old model vs. new model."

## What's in here

- `kb/` — 4 dummy SkyBridge Airlines policy docs (baggage, refunds, change
  fees, loyalty program). Used by the app's own naive RAG for the
  **unguarded** path.
- `rails/kb/` — an identical copy of those docs. NeMo Guardrails uses its
  own built-in knowledge base support to ground and fact-check the
  **guarded** path. Keep the two folders in sync if you edit the docs.
- `rails/config.yml` + `rails/flows.co` — the guardrails config: input rail
  (jailbreak/off-topic check), output rail (policy compliance check), and a
  fact-check rail against the retrieved docs. Embeddings are pinned to
  OpenAI (`text-embedding-3-small`) everywhere, so nothing in this project
  ever calls huggingface.co.
- `model_config.py` — single place the model is defined; both paths import it.
- `rag.py` — FAISS + OpenAI embeddings retrieval for the unguarded path.
- `nist_mapping.py` — maps each rail (and the red-team suite, and LangSmith
  tracing) to specific NIST AI RMF (NIST AI 100-1) subcategories, with the
  actual published subcategory text.
- `guardrails_trace.py` — shared helper that calls the guarded path with
  rail-activation logging enabled and returns which rails fired plus an
  ordered pipeline view, mapped to NIST categories. Used by both `app.py`
  and `run_redteam.py`.
- `ssl_workaround.py` — optional, opt-in SSL verification bypass for
  corporate-proxy environments (see the SSL section below).
- `app.py` — the Streamlit UI: chat with avatars, a live per-message
  guardrail flow diagram, rail-status badges with NIST tooltips, and a
  "NIST AI RMF coverage" panel in the sidebar.
- `redteam_prompts.json` — 8 adversarial prompts: direct jailbreak, roleplay
  jailbreak, indirect prompt injection (hidden instruction inside a fake
  customer review), hallucination bait, off-topic/competitor comparison, PII
  in input, an authorization-bypass attempt, and a prompt-extraction attempt.
- `run_redteam.py` — runs all 8 against both paths, logs which rails fired,
  their NIST category, and the pipeline path, and saves
  `redteam_results.csv` — this is your actual interview artifact.

## NIST AI RMF mapping

There's no SDK to "integrate" against NIST AI RMF - it's a governance
framework, not a library. What this project does instead is map each
concrete piece of the system to a specific, real NIST AI RMF subcategory,
and surface that mapping live in the UI rather than just claiming it in a
README:

| Component | NIST AI RMF Subcategory | What it covers |
|---|---|---|
| `self check input` rail | MEASURE 2.7 | Security & resilience evaluation (adversarial testing) |
| `self check output` rail | MEASURE 2.6 | Safety evaluations - failure modes, misuse scenarios |
| `self check facts` rail | MEASURE 2.5 | Validity, reliability, accuracy (hallucination detection) |
| Red-team suite | MEASURE 2.7 + MANAGE 1.3 | Adversarial testing; documented response to high-priority risks |
| LangSmith tracing | GOVERN 1.5 + MEASURE 3.2 | Ongoing monitoring/periodic review; risk tracking |
| Output-rail policy rules | GOVERN 1.2 | Organizational risk tolerance, defined and enforced |
| Knowledge-base scoping | MAP 1.1 | Intended purpose and context of use documented |

See `nist_mapping.py` for the full mapping including the actual NIST
subcategory text. In Guarded mode, every chat response shows a flow diagram
of which rail stage ran, passed, or blocked - plus badges with the NIST tag
(hover for the full subcategory text and what that rail does).

## Setup

```bash
chmod +x setup.sh   # first time only
./setup.sh
```

That creates a venv, installs dependencies, and copies `.env.example` to
`.env` if it doesn't exist yet. **Edit `.env` and add your own personal
OpenAI API key** (not a corporate-issued one — this is personal interview
prep).

Or do it manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run the chat UI

```bash
source venv/bin/activate
streamlit run app.py
```

First run builds a local FAISS index (`.faiss_index/`) over `kb/` — this
calls the OpenAI embeddings API once, then it's cached on disk.

## Run the red-team comparison

```bash
python run_redteam.py
```

Prints each case side-by-side and writes `redteam_results.csv`.

## If you hit an SSL error on the office network

`CERTIFICATE_VERIFY_FAILED` when calling `api.openai.com` almost always
means your corporate proxy is doing TLS inspection and Python doesn't trust
its root CA. Fix:

```bash
open "/Library/Frameworks/Python.framework/Versions/3.12/Install Certificates.command"
```

If that doesn't help, point Python at the corporate CA bundle directly:

```bash
export SSL_CERT_FILE=/path/to/corporate-ca-bundle.pem
export REQUESTS_CA_BUNDLE=/path/to/corporate-ca-bundle.pem
```

**Avoid `pip-system-certs`/`truststore` on macOS** — it can trigger a
`RecursionError` inside `truststore`'s SSLContext patching on Python 3.12.
If you already installed it and hit that error, remove it:
```bash
pip uninstall pip-system-certs truststore -y
```

### Faster workaround, if the proper fix isn't practical right now

Set `DISABLE_SSL_VERIFY=true` in `.env` and restart the app. This turns off
TLS certificate verification for outbound API calls instead of fixing trust
of your corporate proxy's certificate - it's a real security trade-off
(removes protection against man-in-the-middle attacks), so only use it on
a network you already trust, and don't leave it on for anything beyond
local interview prep. Unlike `pip-system-certs`/`truststore`, this doesn't
touch `ssl.SSLContext` internals, so it won't hit the recursion bug above.

## Observability

Fill in the `LANGCHAIN_*` values in `.env` and NeMo Guardrails sends traces
to LangSmith automatically — no extra code. The sidebar shows a direct link
once tracing is enabled. Guarded runs show a multi-span trace (input rail →
dialogue/fact-check → generation → output rail); unguarded runs show a
single flat LLM call.

## A note on cost

`gpt-3.5-turbo` and `text-embedding-3-small` are both inexpensive — running
the full red-team set a few times will cost well under a dollar. Worth
keeping an eye on usage in the OpenAI dashboard if you run it repeatedly.

## Known rough edges

`nemoguardrails`'s exact Colang syntax and generation-options return shape
can shift slightly between versions. This was scaffolded without network
access to actually pip-install and run it end-to-end, so budget time to
debug on first run rather than assuming it works byte-for-byte immediately.

import os
import html
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
from ssl_workaround import maybe_disable_ssl_verification
maybe_disable_ssl_verification()

from model_config import get_llm
from rag import retrieve_context
from nemoguardrails import RailsConfig, LLMRails
from langsmith import traceable
from nist_mapping import NIST_FUNCTIONS
from guardrails_trace import run_guarded_with_trace

st.set_page_config(page_title="SkyBridge Airlines Assistant", page_icon="✈️", layout="wide")

st.markdown("""
<style>
:root { --navy:#17345f; --blue:#356aa0; --line:#d9e1eb; --muted:#6c788a; --soft:#f6f8fb; --amber:#b86718; --amberbg:#fff6eb; }
.sb-header {background:linear-gradient(90deg,#17345f,#356aa0);padding:1.15rem 1.4rem;border-radius:12px;margin-bottom:1.2rem}
.sb-header h1{color:white;margin:0;font-size:1.5rem}.sb-header p{color:#e3edf8;margin:.3rem 0 0;font-size:.9rem}
.flow-title{font-weight:700;color:#172b4d;margin:.75rem 0 .15rem}.flow-sub{color:var(--muted);font-size:.84rem;margin-bottom:.7rem}
.pipeline{display:flex;align-items:stretch;gap:0;overflow-x:auto;padding:.25rem 0 .7rem}
.stage{min-width:150px;max-width:190px;border:1px solid var(--line);border-radius:10px;padding:.75rem;background:white;position:relative}
.stage .num{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.stage .name{font-weight:700;color:#243b5a;margin:.2rem 0}.stage .state{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.stage .detail{font-size:.72rem;color:var(--muted);margin-top:.28rem;line-height:1.35}
.stage.received,.stage.executed{border-color:#b9cbe0;background:#f7faff}.stage.received .state,.stage.executed .state{color:#356aa0}
.stage.blocked{border:2px solid #d58a43;background:var(--amberbg)}.stage.blocked .state{color:#9b4d0b}
.stage.skipped{background:#f5f6f8;border-color:#e1e4e8}.stage.skipped .name,.stage.skipped .state,.stage.skipped .detail{color:#8b95a5}
.connector{min-width:34px;display:flex;align-items:center;justify-content:center;color:#8fa1b7;font-size:1.25rem}
.decision{border-left:4px solid #d58a43;background:#fff8f0;padding:.7rem .9rem;border-radius:7px;margin:.25rem 0 .8rem;color:#5c3b1e;font-size:.86rem}
.trace-card{border:1px solid var(--line);border-radius:10px;padding:.7rem .85rem;margin:.45rem 0;background:#fff}
.trace-head{display:flex;justify-content:space-between;gap:1rem}.trace-name{font-weight:700;color:#243b5a}.badge{font-size:.68rem;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:999px;background:#edf2f7;color:#53657a}.badge.blocked{background:#fff0df;color:#98500f}
.trace-meta{font-size:.76rem;color:var(--muted);margin-top:.25rem}.nist-box{border:1px solid var(--line);border-radius:10px;padding:.85rem;background:#fafbfd;margin:.45rem 0}.nist-fn{font-weight:800;color:#24466f}.nist-practice{font-size:.76rem;color:#52647a;margin:.15rem 0 .45rem}.nist-copy{font-size:.79rem;line-height:1.45;color:#34465d}
.legend{font-size:.72rem;color:var(--muted);margin-top:.2rem}.legend span{margin-right:1rem}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="sb-header"><h1>SkyBridge Airlines Assistant</h1><p>NeMo Guardrails runtime enforcement · NIST AI RMF evidence mapping</p></div>', unsafe_allow_html=True)

@st.cache_resource
def load_guarded_rails(): return LLMRails(RailsConfig.from_path("rails"))
@st.cache_resource
def load_unguarded_llm(): return get_llm()
guarded_rails, unguarded_llm = load_guarded_rails(), load_unguarded_llm()

@traceable(name="guarded_assistant_turn", run_type="chain")
def run_guarded(rails, user_input): return run_guarded_with_trace(rails, user_input)

def esc(x): return html.escape(str(x), quote=True)

def render_pipeline(pipeline, event):
    if not pipeline: return
    st.markdown('<div class="flow-title">How NeMo Guardrails handled this request</div><div class="flow-sub">Runtime sequence. Later stages are explicitly shown as skipped when an earlier rail stops the turn.</div>', unsafe_allow_html=True)
    cards=[]
    for i,s in enumerate(pipeline,1):
        card=f'<div class="stage {esc(s["status"])}"><div class="num">Stage {i}</div><div class="name">{esc(s["label"])}</div><div class="state">{esc(s["status"].replace("_"," "))}</div><div class="detail">{esc(s.get("detail",""))}</div></div>'
        cards.append(card)
    st.markdown('<div class="pipeline">'+('<div class="connector">›</div>'.join(cards))+'</div>', unsafe_allow_html=True)
    if event and event.get("blocked"):
        st.markdown(f'<div class="decision"><strong>Enforcement decision: BLOCK</strong><br>{esc(event["reason"])}<br><span style="color:#7a6755">Blocking control: {esc(event["blocked_at"])}</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="legend"><span>Executed = stage ran</span><span>Blocked = NeMo stopped the turn</span><span>Skipped = stage did not run</span></div>', unsafe_allow_html=True)

def render_trace(trace):
    if not trace: return
    with st.expander("NeMo execution trace", expanded=any(x["blocked"] for x in trace)):
        st.caption("Technical runtime evidence reported by NeMo Guardrails. NIST mappings below are explanatory mappings made by this demo, not NIST enforcement decisions.")
        for item in trace:
            cls="blocked" if item["blocked"] else ""
            st.markdown(f'<div class="trace-card"><div class="trace-head"><span class="trace-name">{esc(item["name"])}</span><span class="badge {cls}">{esc(item["status"])}</span></div><div class="trace-meta">Control purpose: {esc(item["description"])}</div><div class="trace-meta">Runtime interpretation: {esc(item["runtime_reason"])}</div><div class="trace-meta">Relevant NIST mapping: {esc(item["category"])} · {esc(item["label"])}</div></div>', unsafe_allow_html=True)

def render_nist(event):
    if not event or not event.get("nist"): return
    mapping=event["nist"]
    with st.expander("NIST AI RMF analysis for this event", expanded=True):
        st.info("NeMo Guardrails performed the enforcement. NIST AI RMF is used here to organize the risk-management rationale and evidence; this is not a claim of NIST certification or compliance.")
        st.write(mapping["summary"])
        tabs=st.tabs(["GOVERN","MAP","MEASURE","MANAGE"])
        for tab,fn in zip(tabs,["GOVERN","MAP","MEASURE","MANAGE"]):
            d=mapping["functions"][fn]
            with tab:
                st.markdown(f'<div class="nist-box"><div class="nist-fn">{fn}</div><div class="nist-practice">{esc(d["practice"])}</div><div class="nist-copy"><strong>How it applies</strong><br>{esc(d["applies"])}<br><br><strong>Evidence from this turn</strong><br>{esc(d["evidence"])}</div></div>', unsafe_allow_html=True)

mode=st.sidebar.radio("Mode",["Unguarded","Guarded (NeMo Guardrails)"])
st.sidebar.markdown("---")
st.sidebar.markdown("**Model:** `gpt-3.5-turbo`\n\n**Docs:** baggage, refunds, change fees, loyalty + synthetic sensitive-data demo records")
st.sidebar.markdown("---")
if os.getenv("LANGCHAIN_TRACING_V2","").lower()=="true": st.sidebar.markdown(f"[View traces on LangSmith ↗](https://smith.langchain.com/)\n\nProject: `{os.getenv('LANGCHAIN_PROJECT','default')}`")
else: st.sidebar.caption("LangSmith tracing is off — set LANGCHAIN_TRACING_V2=true in .env to enable it.")
st.sidebar.markdown("---")
if st.sidebar.button("Clear conversation"): st.session_state.history=[]; st.rerun()
with st.sidebar.expander("NIST AI RMF coverage"):
    st.caption("Framework mapping for the demo; NeMo provides runtime enforcement.")
    for fn,info in NIST_FUNCTIONS.items():
        st.markdown(f"**{fn}** — {info['description']}")
        for line in info["coverage"]: st.markdown(f"- {line}")

if "history" not in st.session_state: st.session_state.history=[]
for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
        if turn["role"]=="assistant":
            render_pipeline(turn.get("pipeline"),turn.get("event")); render_trace(turn.get("trace")); render_nist(turn.get("event"))

user_input=st.chat_input("Ask about your booking, baggage, refund, or loyalty status...")
if user_input:
    st.session_state.history.append({"role":"user","content":user_input})
    with st.chat_message("user"): st.write(user_input)
    with st.chat_message("assistant"):
        if mode=="Unguarded":
            context=retrieve_context(user_input)
            prompt="You are a helpful SkyBridge Airlines customer support assistant. Use the context below to answer the user's question.\n\n"+f"Context:\n{context}\n\nUser question: {user_input}"
            answer=unguarded_llm.invoke(prompt).content; trace=pipeline=event=None
        else:
            answer,trace,pipeline,event=run_guarded(guarded_rails,user_input)
        st.write(answer); render_pipeline(pipeline,event); render_trace(trace); render_nist(event)
    st.session_state.history.append({"role":"assistant","content":answer,"trace":trace,"pipeline":pipeline,"event":event})

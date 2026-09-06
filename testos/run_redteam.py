"""
Runs the red-team prompt set against BOTH the unguarded and guarded assistant,
prints a side-by-side comparison including which rails fired, their NIST
AI RMF mapping, and exactly where the guarded pipeline was halted, then saves
the results to a CSV you can drop straight into an interview deck.

Usage:
    python run_redteam.py
"""

import csv
import json

from dotenv import load_dotenv

load_dotenv()

from ssl_workaround import maybe_disable_ssl_verification

maybe_disable_ssl_verification()

from model_config import get_llm
from rag import retrieve_context
from nemoguardrails import RailsConfig, LLMRails
from langsmith import traceable
from guardrails_trace import run_guarded_with_trace


def run_unguarded(llm, prompt: str) -> str:
    context = retrieve_context(prompt)
    full_prompt = (
        "You are a helpful SkyBridge Airlines customer support assistant. "
        "Use the context below to answer the user's question.\n\n"
        f"Context:\n{context}\n\nUser question: {prompt}"
    )
    return llm.invoke(full_prompt).content


@traceable(name="guarded_assistant_turn", run_type="chain")
def run_guarded(rails: LLMRails, prompt: str):
    return run_guarded_with_trace(rails, prompt)


def format_trace(trace):
    if not trace:
        return "(no mapped rails fired)"
    parts = []
    for item in trace:
        status = "BLOCKED" if item["blocked"] else "passed"
        parts.append(f"{item['name']} [{status}, NIST {item['category']}]")
    return "; ".join(parts)


def format_pipeline(pipeline):
    if not pipeline:
        return ""
    return " -> ".join(f"{stage['label']}={stage['status']}" for stage in pipeline)


def main():
    llm = get_llm()
    config = RailsConfig.from_path("rails")
    rails = LLMRails(config)

    with open("redteam_prompts.json") as f:
        cases = json.load(f)

    rows = []
    for case in cases:
        unguarded_answer = run_unguarded(llm, case["prompt"])
        guarded_answer, trace, pipeline, event = run_guarded(rails, case["prompt"])
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "prompt": case["prompt"],
                "unguarded_response": unguarded_answer,
                "guarded_response": guarded_answer,
                "guarded_rails_fired": format_trace(trace),
                "guarded_pipeline": format_pipeline(pipeline),
            }
        )
        print(f"\n=== {case['id']} ({case['category']}) ===")
        print(f"PROMPT:    {case['prompt']}")
        print(f"UNGUARDED: {unguarded_answer}")
        print(f"GUARDED:   {guarded_answer}")
        print(f"RAILS:     {format_trace(trace)}")
        print(f"PIPELINE:  {format_pipeline(pipeline)}")

    with open("redteam_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "category",
                "prompt",
                "unguarded_response",
                "guarded_response",
                "guarded_rails_fired",
                "guarded_pipeline",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved results to redteam_results.csv - this CSV is itself a NIST MEASURE 2.7 evidence artifact.")


if __name__ == "__main__":
    main()

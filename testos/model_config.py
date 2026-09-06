"""
Single source of truth for which model powers BOTH the unguarded and guarded
paths. Keeping this in one place is deliberate: the only variable that should
change between the two demo modes is whether NeMo Guardrails wraps the model,
not which model is used. Otherwise you're comparing two different models, not
guarded vs. unguarded.
"""

import os
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
    )

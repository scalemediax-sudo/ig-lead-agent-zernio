import os
import json
import logging

from groq import Groq

logger = logging.getLogger(__name__)

_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """\
You are a friendly lead qualification assistant for an Instagram business DM inbox.
Your job is to have a natural, conversational chat and collect exactly 3 pieces of information:

1. BUDGET      — What is their approximate budget for the product/service?
2. TIMELINE    — When are they looking to get started (urgency)?
3. COMPANY SIZE — Are they a solo freelancer, small/medium business, or large enterprise?

Rules:
- Be warm, casual, and conversational — this is Instagram DM, not a sales call
- Ask only ONE question per message
- Briefly acknowledge their previous answer before moving to the next question
- Keep every message under 3 sentences
- If they ask what your business offers, give a short friendly answer then steer back to their needs
- Do NOT ask clarifying sub-questions — just move to the next required field
- Once all 3 pieces are collected, thank them warmly and say a team member will reach out soon with a tailored offer

After your conversational reply, on a NEW LINE append exactly this (the system reads it, the user never sees it):
LEAD_DATA:{"budget":"<value or null>","timeline":"<value or null>","company_size":"<value or null>","qualified":<true|false>}

Rules for the JSON:
- Use null (not "null") when a field hasn't been collected yet
- Set "qualified": true ONLY when all three fields are non-null strings
- Output raw compact JSON — no spaces, no line breaks inside it
"""


def process_message(messages: list) -> tuple[str, dict]:
    """
    Given the conversation history (list of {"role": ..., "content": ...} dicts),
    return (reply_text_to_send, lead_data_dict).
    """
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        groq_messages.append({"role": msg["role"], "content": msg["content"]})

    completion = _client.chat.completions.create(
        model=MODEL,
        messages=groq_messages,
        temperature=0.7,
        max_tokens=400,
    )

    raw = completion.choices[0].message.content.strip()
    logger.debug("Groq raw output: %s", raw)

    lead_data: dict = {
        "budget": None,
        "timeline": None,
        "company_size": None,
        "qualified": False,
    }
    reply_text = raw

    if "LEAD_DATA:" in raw:
        head, _, tail = raw.partition("LEAD_DATA:")
        reply_text = head.strip()
        try:
            lead_data = json.loads(tail.strip())
        except json.JSONDecodeError as exc:
            logger.warning("Could not parse LEAD_DATA JSON — %s | raw tail: %.200s", exc, tail)

    return reply_text, lead_data

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

load_dotenv()

import database
import agent
import zernio_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("ZERNIO_WEBHOOK_SECRET", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    logger.info("Database initialised")
    yield


app = FastAPI(title="Instagram Lead Qualifier", lifespan=lifespan)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Qualified leads viewer ────────────────────────────────────────────────────

@app.get("/leads")
async def get_leads():
    """Return all fully-qualified leads (for quick inspection)."""
    return database.get_all_qualified_leads()


# ── Zernio webhook ────────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request):
    # Verify shared secret when configured
    if WEBHOOK_SECRET:
        provided = request.headers.get("X-Zernio-Secret", "")
        if provided != WEBHOOK_SECRET:
            logger.warning("Rejected webhook — invalid secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload = await request.json()
    logger.info("Incoming webhook: %s", payload)

    event = payload.get("event")
    if event != "message.received":
        return JSONResponse({"status": "ignored", "event": event})

    # ── Parse payload ─────────────────────────────────────────────────────────
    # Zernio wraps data in top-level keys: conversation, message, account.
    # Adjust the field paths below if the actual payload differs —
    # check the logged raw payload on first run.
    conversation_obj = payload.get("conversation", {})
    message_obj      = payload.get("message", {})
    account_obj      = payload.get("account", {})
    sender_obj       = message_obj.get("sender", conversation_obj.get("participant", {}))

    conversation_id = (
        conversation_obj.get("id")
        or payload.get("conversation_id")  # fallback flat key
    )
    message_text = message_obj.get("text", "").strip()
    sender_id    = sender_obj.get("id", "")
    sender_name  = (
        sender_obj.get("name")
        or sender_obj.get("username")
        or "there"
    )
    platform = account_obj.get("platform", "instagram")

    if not conversation_id or not message_text:
        logger.warning(
            "Skipping — missing fields. conversation_id=%s text=%r",
            conversation_id, message_text,
        )
        return JSONResponse({"status": "skipped", "reason": "missing fields"})

    # ── Load / create conversation ────────────────────────────────────────────
    conv = database.get_conversation(conversation_id)
    if not conv:
        database.upsert_conversation(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            platform=platform,
        )
        conv = database.get_conversation(conversation_id)

    if conv["stage"] == "qualified":
        logger.info("Conversation %s already qualified — skipping", conversation_id)
        return JSONResponse({"status": "skipped", "reason": "already qualified"})

    # ── Build history + call AI ───────────────────────────────────────────────
    messages = conv["messages"]
    messages.append({"role": "user", "content": message_text})

    reply_text, lead_data = agent.process_message(messages)

    messages.append({"role": "assistant", "content": reply_text})

    stage = "qualified" if lead_data.get("qualified") else "active"
    database.upsert_conversation(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_name=sender_name,
        platform=platform,
        messages=messages,
        lead_data=lead_data,
        stage=stage,
    )

    # ── Send reply ────────────────────────────────────────────────────────────
    await zernio_client.send_message(conversation_id, reply_text)

    if stage == "qualified":
        logger.info(
            "LEAD QUALIFIED — sender=%s  data=%s", sender_name, lead_data
        )

    return JSONResponse({
        "status": "ok",
        "stage": stage,
        "qualified": lead_data.get("qualified", False),
    })

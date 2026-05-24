import os
import logging

import httpx

logger = logging.getLogger(__name__)

ZERNIO_BASE_URL = "https://zernio.com/api/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('ZERNIO_API_KEY', '')}",
        "Content-Type": "application/json",
    }


async def send_message(conversation_id: str, text: str) -> dict:
    """Send a DM reply via Zernio's unified inbox API."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{ZERNIO_BASE_URL}/messages",
                headers=_headers(),
                json={"conversation_id": conversation_id, "text": text},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Zernio send_message HTTP %s: %s",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Zernio send_message failed: %s", e)
            raise

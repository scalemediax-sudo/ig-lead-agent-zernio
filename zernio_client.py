import os
import logging

import httpx

logger = logging.getLogger(__name__)

ZERNIO_BASE_URL = "https://api.zernio.com/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('ZERNIO_API_KEY', '')}",
        "Content-Type": "application/json",
    }


async def send_message(conversation_id: str, text: str, account_id: str) -> dict:
    """Send a DM reply via Zernio inbox API."""
    url = f"{ZERNIO_BASE_URL}/inbox/conversations/{conversation_id}/messages"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                url,
                headers=_headers(),
                json={"accountId": account_id, "message": text},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Zernio send_message HTTP %s: %s",
                e.response.status_code,
                e.response.text[:300],
            )
            raise
        except Exception as e:
            logger.error("Zernio send_message failed: %s", e)
            raise

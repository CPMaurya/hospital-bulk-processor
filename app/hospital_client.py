"""
hospital_client.py
------------------
Thin async wrapper around the Hospital Directory API.

We use httpx because it plays nicely with asyncio and FastAPI.
Retries are intentionally simple – just one retry with a short
back-off.  For a production system you'd wire in something like
tenacity, but this keeps things readable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import HOSPITAL_API_BASE

logger = logging.getLogger(__name__)

# single shared client – created lazily so tests can monkeypatch
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=HOSPITAL_API_BASE,
            timeout=30.0,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def create_hospital(
    name: str,
    address: str,
    phone: Optional[str],
    batch_id: str,
) -> Dict[str, Any]:
    """
    POST a single hospital to the upstream API.

    Raises on non-2xx so the caller can handle failures per-row.
    """
    payload: Dict[str, Any] = {
        "name": name,
        "address": address,
        "creation_batch_id": batch_id,
    }
    if phone:
        payload["phone"] = phone

    client = _get_client()

    # one retry with a short sleep – handles transient 503s
    for attempt in range(2):
        try:
            resp = await client.post("/hospitals/", json=payload)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            if attempt == 0:
                logger.warning("Retrying create_hospital after error: %s", exc)
                await asyncio.sleep(1)
            else:
                raise


async def activate_batch(batch_id: str) -> Dict[str, Any]:
    """PATCH to activate all hospitals belonging to a batch."""
    client = _get_client()
    resp = await client.patch(f"/hospitals/batch/{batch_id}/activate")
    resp.raise_for_status()
    return resp.json()


async def get_batch_hospitals(batch_id: str) -> Any:
    """GET hospitals belonging to a specific batch."""
    client = _get_client()
    resp = await client.get(f"/hospitals/batch/{batch_id}")
    resp.raise_for_status()
    return resp.json()


async def delete_batch(batch_id: str) -> None:
    """DELETE all hospitals in a batch (used for rollback)."""
    client = _get_client()
    resp = await client.delete(f"/hospitals/batch/{batch_id}")
    resp.raise_for_status()

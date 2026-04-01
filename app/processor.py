"""
processor.py
------------
The "brain" of the bulk processing pipeline.

Takes parsed CSV rows → fires concurrent API calls (bounded by a semaphore)
→ activates the batch → returns a BulkResponse.

We also keep an in-memory dict of batch statuses so the optional
GET /hospitals/bulk/{batch_id}/status endpoint can report progress.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Dict

from app.config import CONCURRENCY_LIMIT
from app.hospital_client import activate_batch, create_hospital
from app.schemas import (
    BatchStatus,
    BulkResponse,
    HospitalResult,
    HospitalRow,
)

logger = logging.getLogger(__name__)

# simple in-memory store keyed by batch_id
batch_store: Dict[str, BatchStatus] = {}


async def process_bulk(rows: list[HospitalRow]) -> BulkResponse:
    """
    Main entry point.  Processes a list of validated hospital rows
    against the upstream API and returns a summary.
    """
    batch_id = str(uuid.uuid4())
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    start = time.monotonic()

    # initialise tracking record
    batch_store[batch_id] = BatchStatus(
        batch_id=batch_id,
        status="processing",
        total=len(rows),
        processed=0,
        failed=0,
        activated=False,
        hospitals=[],
    )

    async def _create_one(row: HospitalRow) -> HospitalResult:
        async with sem:
            try:
                data = await create_hospital(
                    name=row.name,
                    address=row.address,
                    phone=row.phone,
                    batch_id=batch_id,
                )
                result = HospitalResult(
                    row=row.row_number,
                    hospital_id=data.get("id"),
                    name=row.name,
                    status="created",
                )
            except Exception as exc:
                logger.error("Row %d failed: %s", row.row_number, exc)
                result = HospitalResult(
                    row=row.row_number,
                    name=row.name,
                    status="failed",
                    error=str(exc),
                )

            # update progress in-place
            status = batch_store[batch_id]
            status.hospitals.append(result)
            if result.status == "failed":
                status.failed += 1
            else:
                status.processed += 1
            return result

    # fan out, bounded by the semaphore
    results = await asyncio.gather(*[_create_one(r) for r in rows])

    # try to activate if nothing failed
    activated = False
    failed_count = sum(1 for r in results if r.status == "failed")

    if failed_count == 0:
        try:
            await activate_batch(batch_id)
            activated = True
            for r in results:
                r.status = "created_and_activated"
        except Exception as exc:
            logger.error("Batch activation failed: %s", exc)
    else:
        logger.warning(
            "Skipping activation for batch %s – %d rows failed",
            batch_id,
            failed_count,
        )

    elapsed = round(time.monotonic() - start, 2)

    # finalise the stored status
    final_status = "completed" if failed_count == 0 else "partially_failed"
    if failed_count == len(rows):
        final_status = "failed"

    batch_store[batch_id] = BatchStatus(
        batch_id=batch_id,
        status=final_status,
        total=len(rows),
        processed=len(rows) - failed_count,
        failed=failed_count,
        activated=activated,
        hospitals=list(results),
    )

    return BulkResponse(
        batch_id=batch_id,
        total_hospitals=len(rows),
        processed_hospitals=len(rows) - failed_count,
        failed_hospitals=failed_count,
        processing_time_seconds=elapsed,
        batch_activated=activated,
        hospitals=list(results),
    )

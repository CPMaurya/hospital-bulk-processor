"""
routes.py
---------
All the HTTP endpoints live here.  Kept in one file because the
surface area is small – three endpoints total.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.csv_parser import parse_hospital_csv
from app.processor import batch_store, process_bulk
from app.schemas import BatchStatus, BulkResponse, ValidationResult

router = APIRouter()


@router.post("/hospitals/bulk", response_model=BulkResponse)
async def bulk_create_hospitals(file: UploadFile = File(...)):
    """
    Accept a CSV upload, validate it, push every row to the Hospital
    Directory API under one batch, activate the batch, and return
    a summary.
    """
    if file.content_type and file.content_type not in (
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Expected a CSV file, got '{file.content_type}'.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    rows, errors = parse_hospital_csv(raw)

    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    result = await process_bulk(rows)
    return result


@router.get("/hospitals/bulk/{batch_id}/status", response_model=BatchStatus)
async def get_batch_status(batch_id: str):
    """
    Poll this to check how a batch is doing.
    Handy if you're watching progress from a frontend.
    """
    status = batch_store.get(batch_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return status


@router.post("/hospitals/bulk/validate", response_model=ValidationResult)
async def validate_csv(file: UploadFile = File(...)):
    """
    Dry-run CSV validation.  Returns whether the file would be
    accepted and any issues found – without actually creating
    anything in the upstream API.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    rows, errors = parse_hospital_csv(raw)

    return ValidationResult(
        valid=len(errors) == 0,
        row_count=len(rows),
        errors=errors,
    )

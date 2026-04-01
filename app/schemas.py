"""
Schemas – plain pydantic models used for validation and serialisation.
Nothing fancy, just mirrors what the spec asks for.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class HospitalRow(BaseModel):
    """One row coming out of the CSV after parsing."""
    row_number: int
    name: str
    address: str
    phone: Optional[str] = None


class HospitalResult(BaseModel):
    """Result of processing a single row."""
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str  # "created_and_activated", "failed", etc.
    error: Optional[str] = None


class BulkResponse(BaseModel):
    """Top-level response for POST /hospitals/bulk."""
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[HospitalResult]


class BatchStatus(BaseModel):
    """Stored snapshot of a batch so we can query it later."""
    batch_id: str
    status: str  # "processing", "completed", "partially_failed", "failed"
    total: int
    processed: int
    failed: int
    activated: bool
    hospitals: List[HospitalResult]


class ValidationResult(BaseModel):
    """Response for the CSV validation endpoint."""
    valid: bool
    row_count: int
    errors: List[str]

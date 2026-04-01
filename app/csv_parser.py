"""
csv_parser.py
-------------
Reads an uploaded CSV file, does basic sanity checks, and hands back
a list of HospitalRow objects (or a list of error strings).

We deliberately keep this as a pure function – no side effects,
easy to unit test.
"""

from __future__ import annotations

import csv
import io
from typing import List, Tuple

from app.schemas import HospitalRow
from app.config import MAX_CSV_ROWS


def parse_hospital_csv(raw_bytes: bytes) -> Tuple[List[HospitalRow], List[str]]:
    """
    Parse raw CSV bytes into hospital rows.

    Returns (rows, errors).  If errors is non-empty, the caller
    should probably reject the upload.
    """
    errors: List[str] = []

    try:
        text = raw_bytes.decode("utf-8-sig")  # utf-8-sig handles BOM from Excel
    except UnicodeDecodeError:
        return [], ["File is not valid UTF-8."]

    reader = csv.DictReader(io.StringIO(text))

    # normalise header names (strip whitespace, lowercase)
    if reader.fieldnames is None:
        return [], ["CSV file appears to be empty or has no header row."]

    clean_fields = [f.strip().lower() for f in reader.fieldnames]

    # we need at least name and address
    if "name" not in clean_fields:
        errors.append("Missing required column: 'name'.")
    if "address" not in clean_fields:
        errors.append("Missing required column: 'address'.")
    if errors:
        return [], errors

    rows: List[HospitalRow] = []

    for i, raw_row in enumerate(reader, start=1):
        # normalise keys
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        name = row.get("name", "")
        address = row.get("address", "")
        phone = row.get("phone", "") or None

        if not name:
            errors.append(f"Row {i}: 'name' is empty.")
            continue
        if not address:
            errors.append(f"Row {i}: 'address' is empty.")
            continue

        rows.append(HospitalRow(
            row_number=i,
            name=name,
            address=address,
            phone=phone,
        ))

    if len(rows) + len(errors) == 0:
        errors.append("CSV file contains no data rows.")

    if len(rows) > MAX_CSV_ROWS:
        errors.append(
            f"CSV contains {len(rows)} valid rows, max allowed is {MAX_CSV_ROWS}."
        )

    return rows, errors

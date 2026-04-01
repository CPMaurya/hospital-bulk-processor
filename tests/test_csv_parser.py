"""
Tests for the CSV parsing logic.

Run with:  pytest tests/ -v
"""

import pytest

from app.csv_parser import parse_hospital_csv


def _make_csv(*lines: str) -> bytes:
    """Helper – joins lines into a UTF-8 CSV blob."""
    return "\n".join(lines).encode("utf-8")


# ---- happy path ----

def test_basic_csv():
    data = _make_csv(
        "name,address,phone",
        "City Hospital,123 Main St,555-0100",
        "Rural Clinic,456 Oak Ave,555-0200",
    )
    rows, errors = parse_hospital_csv(data)
    assert errors == []
    assert len(rows) == 2
    assert rows[0].name == "City Hospital"
    assert rows[1].phone == "555-0200"


def test_phone_is_optional():
    data = _make_csv(
        "name,address,phone",
        "NoPhone Hospital,789 Elm St,",
    )
    rows, errors = parse_hospital_csv(data)
    assert errors == []
    assert rows[0].phone is None


def test_phone_column_missing_entirely():
    """If the CSV has no phone column at all, that's fine."""
    data = _make_csv(
        "name,address",
        "Tiny Clinic,1 Short Rd",
    )
    rows, errors = parse_hospital_csv(data)
    assert errors == []
    assert rows[0].phone is None


# ---- validation failures ----

def test_missing_name_column():
    data = _make_csv("address,phone", "123 St,555")
    rows, errors = parse_hospital_csv(data)
    assert any("name" in e.lower() for e in errors)


def test_empty_name_skipped():
    data = _make_csv(
        "name,address,phone",
        ",123 Main St,555-0000",
    )
    rows, errors = parse_hospital_csv(data)
    assert len(rows) == 0
    assert any("name" in e.lower() for e in errors)


def test_too_many_rows():
    header = "name,address,phone"
    body = [f"Hospital {i},Addr {i},555-{i:04d}" for i in range(25)]
    data = _make_csv(header, *body)
    rows, errors = parse_hospital_csv(data)
    assert any("max" in e.lower() for e in errors)


def test_empty_file():
    rows, errors = parse_hospital_csv(b"")
    assert len(rows) == 0
    assert len(errors) > 0


def test_header_whitespace_tolerance():
    """Columns with extra whitespace should still be recognised."""
    data = _make_csv(
        " Name , Address , Phone ",
        "Test Hospital,99 Test Rd,555-9999",
    )
    rows, errors = parse_hospital_csv(data)
    assert errors == []
    assert rows[0].name == "Test Hospital"


def test_utf8_bom():
    """Excel loves to stick a BOM at the front. Make sure we handle it."""
    bom = b"\xef\xbb\xbf"
    csv_body = b"name,address,phone\nBOM Hospital,1 BOM St,555\n"
    rows, errors = parse_hospital_csv(bom + csv_body)
    assert errors == []
    assert rows[0].name == "BOM Hospital"

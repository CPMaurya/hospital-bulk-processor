"""
Integration tests for the FastAPI endpoints.

These mock out the upstream Hospital Directory API so we don't
hit the real service during CI.
"""

import io
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CSV = "name,address,phone\nGeneral Hospital,123 Main St,555-1234\nCity Clinic,456 Oak Ave,\n"


def _mock_create_response(call_count=[0]):
    """Returns a fake hospital dict, incrementing the ID each time."""
    call_count[0] += 1
    return {
        "id": call_count[0],
        "name": "test",
        "address": "test",
        "phone": None,
        "creation_batch_id": "fake-batch",
        "active": False,
    }


@patch("app.processor.activate_batch", new_callable=AsyncMock)
@patch("app.processor.create_hospital", new_callable=AsyncMock)
def test_bulk_create_success(mock_create, mock_activate):
    mock_create.side_effect = lambda **kw: {"id": 1, "name": kw["name"]}
    mock_activate.return_value = {"activated": True}

    resp = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", SAMPLE_CSV, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_hospitals"] == 2
    assert body["failed_hospitals"] == 0
    assert body["batch_activated"] is True
    assert len(body["hospitals"]) == 2


@patch("app.processor.activate_batch", new_callable=AsyncMock)
@patch("app.processor.create_hospital", new_callable=AsyncMock)
def test_bulk_create_with_failure(mock_create, mock_activate):
    """If one row fails, we should NOT activate the batch."""
    mock_create.side_effect = [
        {"id": 10, "name": "General Hospital"},
        Exception("upstream 500"),
    ]

    resp = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", SAMPLE_CSV, "text/csv")},
    )
    body = resp.json()

    assert body["failed_hospitals"] == 1
    assert body["batch_activated"] is False
    mock_activate.assert_not_called()


def test_bulk_create_bad_csv():
    bad_csv = "wrong_col,another\nfoo,bar\n"
    resp = client.post(
        "/hospitals/bulk",
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert resp.status_code == 422


def test_validate_csv_endpoint():
    resp = client.post(
        "/hospitals/bulk/validate",
        files={"file": ("hospitals.csv", SAMPLE_CSV, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["row_count"] == 2


def test_validate_csv_catches_errors():
    bad = "name\nOnlyName\n"
    resp = client.post(
        "/hospitals/bulk/validate",
        files={"file": ("bad.csv", bad, "text/csv")},
    )
    body = resp.json()
    assert body["valid"] is False
    assert len(body["errors"]) > 0


@patch("app.processor.activate_batch", new_callable=AsyncMock)
@patch("app.processor.create_hospital", new_callable=AsyncMock)
def test_batch_status_endpoint(mock_create, mock_activate):
    mock_create.return_value = {"id": 1, "name": "test"}
    mock_activate.return_value = {}

    # first create a batch
    resp = client.post(
        "/hospitals/bulk",
        files={"file": ("hospitals.csv", SAMPLE_CSV, "text/csv")},
    )
    batch_id = resp.json()["batch_id"]

    # now query its status
    status_resp = client.get(f"/hospitals/bulk/{batch_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["batch_id"] == batch_id


def test_batch_status_not_found():
    resp = client.get("/hospitals/bulk/nonexistent-id/status")
    assert resp.status_code == 404


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

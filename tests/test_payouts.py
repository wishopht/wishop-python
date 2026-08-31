import json
from datetime import datetime, timezone

import pytest
import responses

from wishop import (
    PAYOUT_STATUS_PENDING,
    PAYOUT_STATUS_SUCCEEDED,
    UnprocessableError,
    Wishop,
)

BASE_URL = "https://api.test.local"

PAYOUT = {
    "id": "po_7Hn2vB9xQm4tRkLw",
    "recipient_phone": "+50931234567",
    "recipient_name": "Jean Baptiste",
    "currency": "HTG",
    "amount": "150.00",
    "fee": "3.00",
    "status": "SUCCEEDED",
    "fail_reason": None,
    "reference": "June payroll",
    "metadata": {"employee_id": 4471},
    "livemode": True,
    "created_at": "2026-08-31T12:04:11.318Z",
    "completed_at": "2026-08-31T12:04:12.006Z",
}


@pytest.fixture
def client():
    return Wishop("sk_test_key", base_url=BASE_URL)


def envelope(status_code, data, message="ok"):
    return json.dumps(
        {"status_code": status_code, "success": status_code < 400, "message": message, "data": data}
    )


@responses.activate
def test_create_payout_sends_idempotency_key(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/payouts",
        body=envelope(201, PAYOUT, "payout created"),
        status=201,
        content_type="application/json",
    )

    payout = client.payouts.create(
        amount="150.00",
        currency="HTG",
        recipient_phone="+50931234567",
        reference="June payroll",
        idempotency_key="payroll-2026-06-emp-4471",
    )

    request = responses.calls[0].request
    # Required, unlike on charges: the API rejects an un-keyed payout.
    assert request.headers["Idempotency-Key"] == "payroll-2026-06-emp-4471"

    body = json.loads(request.body)
    assert body["recipient_phone"] == "+50931234567"
    assert body["amount"] == "150.00"
    # The name is resolved from the wallet, never sent.
    assert "recipient_name" not in body

    assert payout.status == PAYOUT_STATUS_SUCCEEDED
    assert payout.fee == "3.00"
    assert payout.recipient_name == "Jean Baptiste"
    assert payout.metadata == {"employee_id": 4471}
    assert payout.completed_at == datetime(2026, 8, 31, 12, 4, 12, 6000, tzinfo=timezone.utc)


def test_create_payout_requires_an_idempotency_key(client):
    # The parameter has no default, so omitting it is a TypeError at the call
    # site rather than a request the API would reject.
    with pytest.raises(TypeError):
        client.payouts.create(
            amount="150.00", currency="HTG", recipient_phone="+50931234567"
        )


@responses.activate
def test_accepted_payout_is_pending_not_an_error(client):
    pending = {**PAYOUT, "status": "PENDING", "completed_at": None, "recipient_name": None}
    responses.add(
        responses.POST,
        BASE_URL + "/v1/payouts",
        body=envelope(202, pending, "payout accepted"),
        status=202,
        content_type="application/json",
    )

    payout = client.payouts.create(
        amount="150.00",
        currency="HTG",
        recipient_phone="+50900000006",
        idempotency_key="key-1",
    )

    assert payout.status == PAYOUT_STATUS_PENDING
    assert payout.completed_at is None


@responses.activate
def test_declined_payout_raises_unprocessable(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/payouts",
        body=envelope(422, None, "payout declined: merchant balance insufficient"),
        status=422,
        content_type="application/json",
    )

    with pytest.raises(UnprocessableError) as excinfo:
        client.payouts.create(
            amount="999999.00",
            currency="HTG",
            recipient_phone="+50900000001",
            idempotency_key="key-2",
        )

    assert "balance insufficient" in str(excinfo.value)


@responses.activate
def test_list_payouts_sends_filters(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/payouts",
        body=envelope(200, {"payouts": [PAYOUT], "has_more": True}),
        status=200,
        content_type="application/json",
    )

    result = client.payouts.list(limit=25, status="FAILED", currency="HTG", starting_after="po_prev")

    query = responses.calls[0].request.params
    assert query["limit"] == "25"
    assert query["status"] == "FAILED"
    assert query["currency"] == "HTG"
    assert query["starting_after"] == "po_prev"

    assert len(result.payouts) == 1
    assert result.has_more is True


@responses.activate
def test_retrieve_payout(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/payouts/po_7Hn2vB9xQm4tRkLw",
        body=envelope(200, PAYOUT, "payout retrieved"),
        status=200,
        content_type="application/json",
    )

    payout = client.payouts.retrieve("po_7Hn2vB9xQm4tRkLw")

    assert payout.id == "po_7Hn2vB9xQm4tRkLw"
    assert responses.calls[0].request.url.endswith("/v1/payouts/po_7Hn2vB9xQm4tRkLw")

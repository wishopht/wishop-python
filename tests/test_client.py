import json
from datetime import datetime, timezone

import pytest
import requests
import responses

from wishop import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    ChargeExpiredError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionError,
    RateLimitError,
    UnprocessableError,
    ValidationError,
    Wishop,
    WishopError,
)

BASE_URL = "https://api.test.local"

CHARGE = {
    "id": "ch_3kQ8xR2mVn7pLdYt",
    "order_id": "order_1042",
    "description": "Two large coffees",
    "currency": "HTG",
    "amount": "1500.00",
    "fee_bearer": "merchant",
    "fee": "45.00",
    "net": "1455.00",
    "customer_debit_amount": "1500.00",
    "amount_refunded": "0.00",
    "customer_phone_masked": None,
    "status": "INITIATED",
    "fail_reason": None,
    "return_url": "https://yourstore.com/orders/1042/complete",
    "metadata": {"cart_id": "c_88213"},
    "livemode": False,
    "expires_at": "2026-08-12T15:30:00.000Z",
    "confirmed_at": None,
    "created_at": "2026-08-12T15:00:00.000Z",
    "pay_url": "https://gatewayapi.wishopht.com/pay/9f2c7a1e",
}

REFUND = {
    "id": "re_8Wq3nK6yTf2mBxLp",
    "charge": "ch_3kQ8xR2mVn7pLdYt",
    "amount": "500.00",
    "currency": "HTG",
    "reason": "requested_by_customer",
    "description": None,
    "status": "succeeded",
    "livemode": False,
    "created_at": "2026-08-12T17:22:08.119Z",
}


@pytest.fixture
def client():
    return Wishop("sk_test_key", base_url=BASE_URL)


def envelope(status_code, data, message="ok"):
    return json.dumps(
        {"status_code": status_code, "success": status_code < 400, "message": message, "data": data}
    )


@responses.activate
def test_create_charge_sends_request_and_unwraps_envelope(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/charges",
        body=envelope(201, CHARGE, "charge created"),
        status=201,
        content_type="application/json",
    )

    charge = client.charges.create(
        amount="1500.00",
        currency="HTG",
        order_id="order_1042",
        metadata={"cart_id": "c_88213"},
        idempotency_key="order-1042-attempt-1",
    )

    request = responses.calls[0].request

    assert request.headers["Authorization"] == "Bearer sk_test_key"
    assert request.headers["User-Agent"].startswith("wishop-python/")
    assert request.headers["Idempotency-Key"] == "order-1042-attempt-1"

    body = json.loads(request.body)

    assert body == {
        "amount": "1500.00",
        "currency": "HTG",
        "order_id": "order_1042",
        "metadata": {"cart_id": "c_88213"},
    }

    assert charge.id == "ch_3kQ8xR2mVn7pLdYt"
    assert charge.pay_url == "https://gatewayapi.wishopht.com/pay/9f2c7a1e"
    assert charge.metadata == {"cart_id": "c_88213"}


@responses.activate
def test_create_charge_omits_idempotency_key_by_default(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/charges",
        body=envelope(201, CHARGE),
        status=201,
        content_type="application/json",
    )

    client.charges.create(amount="1500.00", currency="HTG")

    assert "Idempotency-Key" not in responses.calls[0].request.headers


@responses.activate
def test_charge_parses_timestamps_and_nullables(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt",
        body=envelope(200, CHARGE),
        status=200,
        content_type="application/json",
    )

    charge = client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")

    assert charge.created_at == datetime(2026, 8, 12, 15, 0, tzinfo=timezone.utc)
    assert charge.expires_at == datetime(2026, 8, 12, 15, 30, tzinfo=timezone.utc)
    assert charge.confirmed_at is None
    assert charge.fail_reason is None
    assert charge.customer_phone_masked is None


@responses.activate
def test_list_charges_serializes_query_parameters(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges",
        body=envelope(200, {"charges": [CHARGE], "has_more": True}),
        status=200,
        content_type="application/json",
    )

    page = client.charges.list(
        limit=100,
        starting_after="ch_5Tn9wY3pQr8kMxZv",
        status="PAID",
        query="order_1042",
    )

    query = responses.calls[0].request.params

    assert query == {
        "limit": "100",
        "starting_after": "ch_5Tn9wY3pQr8kMxZv",
        "status": "PAID",
        "q": "order_1042",
    }

    assert page.has_more is True
    assert len(page.charges) == 1


@responses.activate
def test_list_charges_omits_unset_parameters(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges",
        body=envelope(200, {"charges": [], "has_more": False}),
        status=200,
        content_type="application/json",
    )

    page = client.charges.list()

    assert responses.calls[0].request.params == {}
    assert page.charges == []
    assert page.has_more is False


@responses.activate
def test_create_refund_posts_to_the_charge(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt/refunds",
        body=envelope(201, REFUND, "refund created"),
        status=201,
        content_type="application/json",
    )

    refund = client.refunds.create(
        "ch_3kQ8xR2mVn7pLdYt",
        amount="500.00",
        reason="requested_by_customer",
    )

    assert json.loads(responses.calls[0].request.body) == {
        "amount": "500.00",
        "reason": "requested_by_customer",
    }

    assert refund.id == "re_8Wq3nK6yTf2mBxLp"
    assert refund.description is None


@responses.activate
def test_create_refund_with_no_arguments_sends_an_empty_body(client):
    responses.add(
        responses.POST,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt/refunds",
        body=envelope(201, REFUND),
        status=201,
        content_type="application/json",
    )

    client.refunds.create("ch_3kQ8xR2mVn7pLdYt")

    assert json.loads(responses.calls[0].request.body) == {}


@responses.activate
def test_list_refunds_returns_a_list(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt/refunds",
        body=envelope(200, {"refunds": [REFUND]}),
        status=200,
        content_type="application/json",
    )

    refunds = client.refunds.list("ch_3kQ8xR2mVn7pLdYt")

    assert len(refunds) == 1
    assert refunds[0].status == "succeeded"


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (403, PermissionError),
        (404, NotFoundError),
        (409, ConflictError),
        (410, ChargeExpiredError),
        (413, PayloadTooLargeError),
        (422, UnprocessableError),
        (429, RateLimitError),
        (500, APIError),
        (503, APIError),
    ],
)
@responses.activate
def test_status_codes_map_to_typed_errors(client, status_code, expected):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_missing",
        body=envelope(status_code, None, "the gateway said no"),
        status=status_code,
        content_type="application/json",
    )

    with pytest.raises(expected) as raised:
        client.charges.retrieve("ch_missing")

    assert isinstance(raised.value, WishopError)
    assert raised.value.status_code == status_code
    assert raised.value.message == "the gateway said no"


@responses.activate
def test_rate_limit_error_carries_retry_after(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt",
        body=envelope(429, None, "rate limit exceeded"),
        status=429,
        headers={"Retry-After": "12"},
        content_type="application/json",
    )

    with pytest.raises(RateLimitError) as raised:
        client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")

    assert raised.value.retry_after == 12


@responses.activate
def test_non_json_failure_still_maps_to_a_typed_error(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt",
        body="<html>upstream unavailable</html>",
        status=502,
        content_type="text/html",
    )

    with pytest.raises(APIError):
        client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")


@responses.activate
def test_transport_failure_raises_a_connection_error(client):
    responses.add(
        responses.GET,
        BASE_URL + "/v1/charges/ch_3kQ8xR2mVn7pLdYt",
        body=requests.ConnectionError("connection reset"),
    )

    with pytest.raises(APIConnectionError):
        client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")

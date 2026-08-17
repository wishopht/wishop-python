import hashlib
import hmac

import pytest

from wishop import SignatureVerificationError, construct_event

PAYLOAD = (
    '{"id":"evt_7Fk2mQ9xLp4nRt8W","type":"charge.refunded","api_version":"2026-08-01",'
    '"created_at":"2026-08-12T17:22:08.559Z","livemode":true,"data":{"object":"charge",'
    '"charge":{"id":"ch_3kQ8xR2mVn7pLdYt","status":"PAID","currency":"HTG","amount":"1500.00",'
    '"amount_refunded":"500.00","livemode":true,"created_at":"2026-08-12T15:00:00.000Z"},'
    '"refund":{"id":"re_8Wq3nK6yTf2mBxLp","charge":"ch_3kQ8xR2mVn7pLdYt","amount":"500.00",'
    '"currency":"HTG","status":"succeeded","livemode":true,'
    '"created_at":"2026-08-12T17:22:08.119Z"}}}'
).encode("utf-8")

NOW = 1754990400


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    monkeypatch.setattr("wishop.webhooks.time.time", lambda: float(NOW))


def sign(secret, timestamp=NOW, payload=PAYLOAD):
    return hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("utf-8") + b"." + payload,
        hashlib.sha256,
    ).hexdigest()


def header(secret="whsec_test", timestamp=NOW, payload=PAYLOAD):
    return "t={},v1={}".format(timestamp, sign(secret, timestamp, payload))


def test_returns_event():
    event = construct_event(PAYLOAD, header(), "whsec_test")

    assert event.id == "evt_7Fk2mQ9xLp4nRt8W"
    assert event.type == "charge.refunded"
    assert event.data.charge.amount_refunded == "500.00"
    assert event.data.refund.id == "re_8Wq3nK6yTf2mBxLp"


def test_accepts_a_string_payload():
    event = construct_event(PAYLOAD.decode("utf-8"), header(), "whsec_test")

    assert event.id == "evt_7Fk2mQ9xLp4nRt8W"


def test_accepts_second_signature_during_rotation():
    rotating = "t={},v1={},v1={}".format(NOW, sign("whsec_previous"), sign("whsec_current"))

    assert construct_event(PAYLOAD, rotating, "whsec_current").type == "charge.refunded"


def test_rejects_timestamp_outside_tolerance():
    stale = NOW - 600

    with pytest.raises(SignatureVerificationError):
        construct_event(PAYLOAD, header(timestamp=stale), "whsec_test")


def test_accepts_stale_timestamp_when_tolerance_disabled():
    stale = NOW - 600

    assert construct_event(PAYLOAD, header(timestamp=stale), "whsec_test", tolerance=0)


def test_rejects_altered_payload():
    altered = PAYLOAD[:-1] + b" }"

    with pytest.raises(SignatureVerificationError):
        construct_event(altered, header(), "whsec_test")


def test_rejects_wrong_secret():
    with pytest.raises(SignatureVerificationError):
        construct_event(PAYLOAD, header(secret="whsec_other"), "whsec_test")


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "not-a-signature",
        "t={}".format(NOW),
        "v1=abc123",
        "t=later,v1=abc123",
        "t={},v1=".format(NOW),
        ",,,",
        "t={},v2=abc123".format(NOW),
    ],
)
def test_rejects_malformed_headers(malformed):
    with pytest.raises(SignatureVerificationError):
        construct_event(PAYLOAD, malformed, "whsec_test")

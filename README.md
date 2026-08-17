# Wishop Python

The official Python client for the [Wishop API](https://docs.wishop.com).

Create charges, send customers to a hosted checkout page, refund them, and verify webhooks.

## Install

```bash
pip install wishop
```

Requires Python 3.9 or later.

## Quickstart

```python
import os

from wishop import Wishop

client = Wishop(os.environ["WISHOP_SECRET_KEY"])

charge = client.charges.create(
    amount="1500.00",
    currency="HTG",
    order_id="order_1042",
    description="Two large coffees",
    return_url="https://yourstore.com/orders/1042/complete",
    metadata={"cart_id": "c_88213"},
)

print(charge.pay_url)
```

Send the customer to `charge.pay_url`. It is returned on create only, so persist it with the order.

When the payment reaches a terminal state, Wishop sends a webhook and returns the customer to your `return_url`. Confirm the outcome from the webhook or by retrieving the charge — never from the redirect alone.

## Configuration

```python
client = Wishop(
    os.environ["WISHOP_SECRET_KEY"],
    timeout=10.0,
    session=my_session,
    base_url="http://localhost:8080",
)
```

| Argument | Default | Notes |
| --- | --- | --- |
| `timeout` | `30.0` | Seconds, applied to every request |
| `session` | a new `requests.Session` | Supply your own for proxies, retries at the transport layer, or custom TLS |
| `base_url` | `https://api.wishop.com` | For pointing at a mock server in your own tests |

Test and live mode are selected by the key, not by configuration. A `sk_test_` key reaches test data; a `sk_live_` key reaches live data.

The client is synchronous. From an async framework, run calls in a worker thread so the event loop is not blocked:

```python
charge = await asyncio.to_thread(client.charges.create, amount="1500.00", currency="HTG")
```

## Charges

```python
charge = client.charges.create(amount="1500.00", currency="HTG")
charge = client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")
page = client.charges.list(status="PAID", limit=100)
```

`list` returns one page. Pass the id of the last charge as `starting_after` while `has_more` is true:

```python
def all_charges(client, status=None):
    starting_after = None

    while True:
        page = client.charges.list(limit=100, status=status, starting_after=starting_after)

        for charge in page.charges:
            yield charge

        if not page.has_more:
            return

        starting_after = page.charges[-1].id
```

Search across charge id and order id with `query`, which maps to the API's `q` parameter.

## Refunds

```python
refund = client.refunds.create(
    "ch_3kQ8xR2mVn7pLdYt",
    amount="500.00",
    reason="requested_by_customer",
)

refunds = client.refunds.list("ch_3kQ8xR2mVn7pLdYt")
```

Omit `amount` to refund everything still refundable. Refund lists are not paginated.

## Money

Amounts are strings, never numbers, and every field that holds money is a string: `amount`, `fee`, `net`, `customer_debit_amount`, `amount_refunded`. Parse them with `Decimal`, never a float.

```python
from decimal import Decimal

amount = Decimal(charge.amount)
```

## Idempotency

Pass a key on charge and refund creation so a retry after a timeout cannot charge twice:

```python
charge = client.charges.create(
    amount="1500.00",
    currency="HTG",
    idempotency_key=f"charge-{order.id}-{order.payment_attempt}",
)
```

Nothing is sent unless you pass it. Derive the key from the payment *attempt*, not the order — reusing an order id replays the previous failure instead of creating the charge a retrying customer needs. Keys are remembered for 24 hours.

## Errors

Every failure raises a typed exception:

```python
from wishop import RateLimitError, UnprocessableError, WishopError

try:
    charge = client.charges.create(amount="1500.00", currency="HTG")
except RateLimitError as exc:
    time.sleep(exc.retry_after or 1)
except UnprocessableError as exc:
    log.warning(exc.message)
except WishopError as exc:
    log.error("wishop failed with %s", exc.status_code)
```

| Exception | Status | Cause |
| --- | --- | --- |
| `ValidationError` | 400 | Malformed body, invalid amount or currency, metadata over the limits |
| `AuthenticationError` | 401 | Missing, malformed, unknown, or revoked key |
| `PermissionError` | 403 | Live key from an address that is not whitelisted |
| `NotFoundError` | 404 | No charge or refund with that id in this mode |
| `ConflictError` | 409 | Idempotency key still in flight, or charge no longer payable |
| `ChargeExpiredError` | 410 | Charge expired |
| `PayloadTooLargeError` | 413 | Upload too large |
| `UnprocessableError` | 422 | Currency not enabled, charge not refundable, refund exceeds remaining, wallet declined |
| `RateLimitError` | 429 | Rate limit exceeded; carries `retry_after` in seconds |
| `APIError` | 5xx and anything unmapped | Failure on the gateway side |
| `APIConnectionError` | — | The request never completed: DNS, TLS, connection reset, or timeout |

All of them subclass `WishopError`, which carries `.status_code` and `.message`.

`PermissionError` shadows the builtin of the same name when imported bare — import it as `from wishop import PermissionError as WishopPermissionError` if that matters in your module.

`.message` is prose and its wording can change — branch on the exception type or `.status_code`, never on the text.

The client does not retry. `ConflictError`, `RateLimitError`, and `APIError` are safe to retry with backoff and the same idempotency key; nothing else is.

## Payment failures

A failed payment is not an exception — the call succeeded, the payment didn't. Read `status` and `fail_reason`:

```python
if charge.status == "FAILED":
    show(EXPLANATIONS.get(charge.fail_reason, "The payment could not be completed."))
```

| `fail_reason` | Meaning |
| --- | --- |
| `INSUFFICIENT_FUNDS` | Wallet balance did not cover the payment |
| `PIN_LOCKED` | Wallet locked after repeated incorrect PINs |
| `OTP_EXPIRED` | One-time code expired before use |
| `OTP_ATTEMPTS_EXCEEDED` | Too many incorrect one-time codes |
| `WALLET_NOT_FOUND` | No wallet for that phone number |
| `DECLINED` | Wallet refused the payment |
| `TIMEOUT` | Confirmation timed out |
| `INTERNAL_ERROR` | Failure on our side |

Keep a default branch — new reasons can be added, and `fail_reason` is a plain string so an unknown value arrives intact rather than failing to parse.

## Webhooks

Verification needs the body **exactly as received**. `request.json` and `request.get_json()` will not do — they hand you a parsed object, and re-serializing it changes whitespace and key order so the signature will never match.

Flask:

```python
from wishop import SignatureVerificationError, construct_event

@app.post("/webhooks/wishop")
def wishop_webhook():
    try:
        event = construct_event(
            request.get_data(),
            request.headers.get("X-Wishop-Signature", ""),
            os.environ["WISHOP_WEBHOOK_SECRET"],
        )
    except SignatureVerificationError:
        return "", 400

    if events.seen(request.headers["X-Webhook-Id"]):
        return "", 200

    if event.type == "charge.paid":
        fulfil(event.data.charge)
    elif event.type == "charge.failed":
        notify_failure(event.data.charge)
    elif event.type == "charge.expired":
        release_stock(event.data.charge)
    elif event.type == "charge.refunded":
        record_refund(event.data.refund)

    return "", 200
```

Django uses `request.body`; FastAPI uses `await request.body()`.

`construct_event` rejects a stale timestamp, an altered body, and a signature that does not match. It accepts a match on any `v1` value, which is what keeps events flowing during a secret rotation. The default tolerance is 300 seconds:

```python
event = construct_event(body, signature, secret, tolerance=60)
```

Delivery is at-least-once, so deduplicate on the `X-Webhook-Id` header, which is stable across retries. Record it in the same transaction as the work it triggers. Respond `2xx` once the event is durably recorded and queue anything slow — you have about ten seconds per attempt.

`event.data.refund` is set only on `charge.refunded`. A partial refund leaves the charge `PAID`; read `amount_refunded`.

## Testing

Test mode uses `sk_test_` keys against the same host. The payment outcome is chosen by the phone number the customer enters — see [test phone numbers](https://docs.wishop.com/testing/test-phone-numbers).

To test your own code against this client, point it at a local server:

```python
client = Wishop("sk_test_key", base_url="http://localhost:8080")
```

## Reference

Field-by-field documentation for the charge, refund, and event objects lives at [docs.wishop.com](https://docs.wishop.com).

## License

MIT

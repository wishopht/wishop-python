# Wishop Python

Python client for the [Wishop API](https://developers.wishopht.com).

Use it to create charges, send customers to the hosted checkout page, issue refunds and payouts, and verify webhooks.

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

Redirect the customer to `charge.pay_url`. The API only returns it when the charge is created, so save it with the order.

When the payment finishes, Wishop sends you a webhook and redirects the customer to your `return_url`. Use the webhook, or retrieve the charge, to confirm the result. Don't rely on the redirect alone.

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
| `session` | a new `requests.Session` | Pass your own for proxies, transport-level retries, or custom TLS |
| `base_url` | `https://gatewayapi.wishopht.com` | Change it to point at a mock server in your tests |

The key decides the mode. A `sk_test_` key uses test data and a `sk_live_` key uses live data.

The client is synchronous. In an async app, run calls in a worker thread so they don't block the event loop:

```python
charge = await asyncio.to_thread(client.charges.create, amount="1500.00", currency="HTG")
```

## Charges

```python
charge = client.charges.create(amount="1500.00", currency="HTG")
charge = client.charges.retrieve("ch_3kQ8xR2mVn7pLdYt")
page = client.charges.list(status="PAID", limit=100)
```

`list` returns one page at a time. To get the next page, pass the id of the last charge as `starting_after`, and stop when `has_more` is false:

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

Use `query` to search by charge id or order id. It is sent as the API's `q` parameter.

## Refunds

```python
refund = client.refunds.create(
    "ch_3kQ8xR2mVn7pLdYt",
    amount="500.00",
    reason="requested_by_customer",
)

refunds = client.refunds.list("ch_3kQ8xR2mVn7pLdYt")
```

Leave out `amount` to refund whatever is left on the charge. Refund lists are not paginated.

## Payouts

A payout sends money from your wallet to a customer's wallet, for example for payroll, marketplace settlements or rewards.

```python
payout = client.payouts.create(
    amount="150.00",
    currency="HTG",
    recipient_phone="+50931234567",
    reference="June payroll",
    idempotency_key=f"payroll-2026-06-{employee.id}",
)

payouts = client.payouts.list(status="FAILED")
one = client.payouts.retrieve("po_7Hn2vB9xQm4tRkLw")
```

`idempotency_key` is required for payouts. Without it, retrying after a dropped connection could send the money twice. Your wallet is debited `amount + fee`.

A payout comes back with one of three statuses. Make sure your code handles `PENDING`:

```python
if payout.status == "SUCCEEDED":
    ...  # The money was sent.
elif payout.status == "PENDING":
    # We didn't get a final answer from the wallet, so the money may or may not have moved.
    # It settles on its own and a webhook tells you the result.
    # Don't create a new payout. If you retry, use the same key.
    ...
```

If the payout is declined, `create` raises `UnprocessableError`, but the payout is still saved as `FAILED` and you can `retrieve` it. A rejected refund is not saved.

## Money

Every money field is a string: `amount`, `fee`, `net`, `customer_debit_amount`, `amount_refunded`. Parse them with `Decimal`, not `float`.

```python
from decimal import Decimal

amount = Decimal(charge.amount)
```

## Idempotency

Pass an idempotency key when creating charges and refunds, so retrying after a timeout can't charge the customer twice:

```python
charge = client.charges.create(
    amount="1500.00",
    currency="HTG",
    idempotency_key=f"charge-{order.id}-{order.payment_attempt}",
)
```

For charges and refunds the key is optional. For payouts it is a required keyword argument, so leaving it out raises a `TypeError` before any request is sent.

Build a charge key from the payment attempt, not just the order. If you reuse the order id, a customer who tries again gets the earlier failed charge back instead of a new one. For payouts, do the opposite: build the key from the payout itself and reuse it on every retry, because a new key creates a second payout. Keys expire after 24 hours.

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
| `ValidationError` | 400 | Malformed body, invalid amount or currency, or metadata over the limits |
| `AuthenticationError` | 401 | Missing, malformed, unknown, or revoked key |
| `PermissionError` | 403 | Live key used from an IP address that is not whitelisted |
| `NotFoundError` | 404 | No charge, refund or payout with that id in this mode, or no wallet for the payout recipient's phone |
| `ConflictError` | 409 | A request with the same idempotency key is still running, the charge can no longer be paid, or your wallet is not set up for live payouts |
| `ChargeExpiredError` | 410 | The charge has expired |
| `PayloadTooLargeError` | 413 | Request body too large |
| `UnprocessableError` | 422 | Currency not enabled, charge not refundable, refund larger than what is left, wallet declined, or payout declined for balance or recipient |
| `RateLimitError` | 429 | Too many requests. `retry_after` gives the wait in seconds |
| `APIError` | 5xx or anything else | Server error on Wishop's side |
| `APIConnectionError` | none | The request didn't complete: DNS, TLS, connection reset, or timeout |

They all inherit from `WishopError`, which has `.status_code` and `.message`.

Importing `PermissionError` directly hides Python's built-in `PermissionError`. If that is a problem, import it under another name: `from wishop import PermissionError as WishopPermissionError`.

The wording of `.message` can change. Check the exception type or `.status_code` in your code, not the message text.

The client never retries on its own. You can retry `ConflictError`, `RateLimitError` and `APIError` with backoff, using the same idempotency key. Don't retry the others.

## Payment failures

A failed payment doesn't raise an exception. The API call worked; the customer's payment did not. Check `status` and `fail_reason`:

```python
if charge.status == "FAILED":
    show(EXPLANATIONS.get(charge.fail_reason, "The payment could not be completed."))
```

| `fail_reason` | Meaning |
| --- | --- |
| `INSUFFICIENT_FUNDS` | Not enough money in the wallet |
| `PIN_LOCKED` | Wallet locked after too many wrong PINs |
| `OTP_EXPIRED` | The one-time code expired |
| `OTP_ATTEMPTS_EXCEEDED` | Too many wrong one-time codes |
| `WALLET_NOT_FOUND` | No wallet for that phone number |
| `DECLINED` | The wallet declined the payment |
| `TIMEOUT` | The customer didn't confirm in time |
| `INTERNAL_ERROR` | Something failed on Wishop's side |

Always have a fallback for reasons you don't recognise, because new ones may be added. `fail_reason` is a plain string, so an unknown value still comes through.

## Webhooks

Verify the signature against the raw request body. Don't use `request.json` or `request.get_json()`: they return parsed JSON, and serializing it again changes the bytes, so the signature won't match.

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
    elif event.type == "payout.succeeded":
        mark_payout_sent(event.data.payout)
    elif event.type == "payout.failed":
        mark_payout_failed(event.data.payout)

    return "", 200
```

In Django, use `request.body`. In FastAPI, use `await request.body()`.

`construct_event` raises `SignatureVerificationError` if the timestamp is too old, the body was changed, or the signature doesn't match. A header can carry several `v1` signatures and one match is enough, so events keep arriving while you rotate your secret. Timestamps up to 300 seconds old are accepted by default. To change that:

```python
event = construct_event(body, signature, secret, tolerance=60)
```

The same event can arrive more than once, so check the `X-Webhook-Id` header, which stays the same on every retry. Save it in the same database transaction as the work the event triggers. Reply with `2xx` as soon as you have saved the event, and do slow work in the background. Each delivery attempt times out after about ten seconds.

`event.data.refund` is only set on `charge.refunded`. After a partial refund the charge stays `PAID`; read `amount_refunded` to see how much was returned.

On `payout.*` events `event.data.charge` is `None`, and on `charge.*` events `event.data.payout` is `None`. `event.data.object` tells you which one is set.

## Testing

Test mode uses `sk_test_` keys on the same API host. The phone number decides what happens: the customer's number for a charge, the recipient's for a payout. Charges and payouts use different test numbers; `+50900000006` gives you a pending payout. See [test phone numbers](https://developers.wishopht.com/testing/test-phone-numbers).

To test your own code without calling Wishop, point the client at a local server:

```python
client = Wishop("sk_test_key", base_url="http://localhost:8080")
```

## Reference

Every field on charges, refunds, payouts and events is documented at [developers.wishopht.com](https://developers.wishopht.com).

## License

MIT

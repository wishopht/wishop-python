# Changelog

## 1.1.0

Payouts — send money from your wallet to a customer's.

- `payouts.create`, `payouts.retrieve`, `payouts.list`
- `Payout` and `PayoutList` dataclasses
- `PAYOUT_STATUS_*` constants, plus
  `FAIL_REASON_INSUFFICIENT_MERCHANT_BALANCE` and
  `FAIL_REASON_RECIPIENT_INELIGIBLE`
- `EVENT_PAYOUT_CREATED`, `EVENT_PAYOUT_SUCCEEDED`, `EVENT_PAYOUT_FAILED`

Fixed: `construct_event` raised `KeyError` on every `payout.*` event, because
`parse_event` read `data["charge"]` unconditionally. It now parses only the
object the event carries.

**Type change:** `EventData.charge` is now `Optional[Charge]` and
`EventData.payout` was added. Code that reads `event.data.charge` without a
`None` check needs one under mypy. Charge events are unchanged at runtime.

`payouts.create` takes `idempotency_key` as a required keyword argument — the
API requires one, and an un-keyed payout retry pays twice.

## 1.0.0

Initial release.

- `charges.create`, `charges.retrieve`, `charges.list`
- `refunds.create`, `refunds.list`
- `construct_event` for webhook signature verification
- Typed exceptions for every documented status code

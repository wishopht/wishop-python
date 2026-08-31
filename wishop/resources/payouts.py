from __future__ import annotations

from typing import Any, Dict, Optional

from .._parsing import parse_payout, parse_payout_list
from .._transport import Transport
from ..types import Payout, PayoutList


class Payouts:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create(
        self,
        *,
        amount: str,
        currency: str,
        recipient_phone: str,
        idempotency_key: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Payout:
        """Send money from your wallet to a customer's.

        ``idempotency_key`` has no default, unlike everywhere else in this
        client: a payout pushes money out, so a retry after a dropped
        connection is indistinguishable from a second, deliberate payment.
        Derive it from the thing being paid for and reuse it across retries — a
        key generated per attempt defeats the mechanism entirely.

        Three outcomes. The returned payout's ``status`` is ``SUCCEEDED`` (the
        money moved) or ``PENDING`` (the wallet's answer was lost — it resolves
        on its own and a webhook reports the outcome; never send a
        replacement). A decline raises ``UnprocessableError`` and still records
        a ``FAILED`` payout you can ``retrieve``.

        There is no recipient name parameter: the name is resolved from the
        wallet and returned on the payout.
        """
        body: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "recipient_phone": recipient_phone,
        }

        if reference is not None:
            body["reference"] = reference

        if metadata is not None:
            body["metadata"] = metadata

        payload = self._transport.request(
            "POST",
            "/v1/payouts",
            body=body,
            idempotency_key=idempotency_key,
        )

        return parse_payout(payload)

    def retrieve(self, payout_id: str) -> Payout:
        """Read one payout — how you check on a pending one, or read a decline."""
        payload = self._transport.request("GET", "/v1/payouts/" + payout_id)

        return parse_payout(payload)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        starting_after: Optional[str] = None,
        status: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> PayoutList:
        params: Dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit

        if starting_after is not None:
            params["starting_after"] = starting_after

        if status is not None:
            params["status"] = status

        if currency is not None:
            params["currency"] = currency

        payload = self._transport.request("GET", "/v1/payouts", params=params)

        return parse_payout_list(payload)

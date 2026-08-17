from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._parsing import parse_refund
from .._transport import Transport
from ..types import Refund


class Refunds:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create(
        self,
        charge_id: str,
        *,
        amount: Optional[str] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Refund:
        body: Dict[str, Any] = {}

        if amount is not None:
            body["amount"] = amount

        if reason is not None:
            body["reason"] = reason

        if description is not None:
            body["description"] = description

        payload = self._transport.request(
            "POST",
            "/v1/charges/" + charge_id + "/refunds",
            body=body,
            idempotency_key=idempotency_key,
        )

        return parse_refund(payload)

    def list(self, charge_id: str) -> List[Refund]:
        payload = self._transport.request("GET", "/v1/charges/" + charge_id + "/refunds")

        return [parse_refund(item) for item in payload.get("refunds", [])]

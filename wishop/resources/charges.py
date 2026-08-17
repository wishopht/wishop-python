from __future__ import annotations

from typing import Any, Dict, Optional

from .._parsing import parse_charge, parse_charge_list
from .._transport import Transport
from ..types import Charge, ChargeList


class Charges:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create(
        self,
        *,
        amount: str,
        currency: str,
        order_id: Optional[str] = None,
        description: Optional[str] = None,
        fee_bearer: Optional[str] = None,
        return_url: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Charge:
        body: Dict[str, Any] = {"amount": amount, "currency": currency}

        if order_id is not None:
            body["order_id"] = order_id

        if description is not None:
            body["description"] = description

        if fee_bearer is not None:
            body["fee_bearer"] = fee_bearer

        if return_url is not None:
            body["return_url"] = return_url

        if metadata is not None:
            body["metadata"] = metadata

        payload = self._transport.request(
            "POST",
            "/v1/charges",
            body=body,
            idempotency_key=idempotency_key,
        )

        return parse_charge(payload)

    def retrieve(self, charge_id: str) -> Charge:
        payload = self._transport.request("GET", "/v1/charges/" + charge_id)

        return parse_charge(payload)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        starting_after: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> ChargeList:
        params: Dict[str, Any] = {}

        if limit is not None:
            params["limit"] = limit

        if starting_after is not None:
            params["starting_after"] = starting_after

        if status is not None:
            params["status"] = status

        if query is not None:
            params["q"] = query

        payload = self._transport.request("GET", "/v1/charges", params=params)

        return parse_charge_list(payload)

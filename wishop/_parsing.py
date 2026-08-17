from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .types import Charge, ChargeList, Event, EventData, Refund


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def parse_charge(payload: Dict[str, Any]) -> Charge:
    return Charge(
        id=payload["id"],
        status=payload["status"],
        currency=payload["currency"],
        amount=payload["amount"],
        livemode=payload["livemode"],
        created_at=parse_datetime(payload["created_at"]),
        order_id=payload.get("order_id"),
        description=payload.get("description"),
        fee_bearer=payload.get("fee_bearer"),
        fee=payload.get("fee"),
        net=payload.get("net"),
        customer_debit_amount=payload.get("customer_debit_amount"),
        amount_refunded=payload.get("amount_refunded"),
        customer_phone_masked=payload.get("customer_phone_masked"),
        fail_reason=payload.get("fail_reason"),
        return_url=payload.get("return_url"),
        metadata=payload.get("metadata") or {},
        expires_at=parse_datetime(payload.get("expires_at")),
        confirmed_at=parse_datetime(payload.get("confirmed_at")),
        pay_url=payload.get("pay_url"),
    )


def parse_refund(payload: Dict[str, Any]) -> Refund:
    return Refund(
        id=payload["id"],
        charge=payload["charge"],
        amount=payload["amount"],
        currency=payload["currency"],
        status=payload["status"],
        livemode=payload["livemode"],
        created_at=parse_datetime(payload["created_at"]),
        reason=payload.get("reason"),
        description=payload.get("description"),
    )


def parse_charge_list(payload: Dict[str, Any]) -> ChargeList:
    return ChargeList(
        charges=[parse_charge(item) for item in payload.get("charges", [])],
        has_more=bool(payload.get("has_more")),
    )


def parse_event(payload: Dict[str, Any]) -> Event:
    data = payload.get("data") or {}
    refund = data.get("refund")

    return Event(
        id=payload["id"],
        type=payload["type"],
        api_version=payload["api_version"],
        created_at=parse_datetime(payload["created_at"]),
        livemode=payload["livemode"],
        data=EventData(
            object=data.get("object", "charge"),
            charge=parse_charge(data["charge"]),
            refund=parse_refund(refund) if refund else None,
        ),
    )

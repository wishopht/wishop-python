from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from .types import Charge, ChargeList, Event, EventData, Payout, PayoutList, Refund


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def parse_required_datetime(value: str) -> datetime:
    parsed = parse_datetime(value)

    if parsed is None:
        raise ValueError("expected a timestamp")

    return parsed


def parse_charge(payload: Dict[str, Any]) -> Charge:
    return Charge(
        id=payload["id"],
        status=payload["status"],
        currency=payload["currency"],
        amount=payload["amount"],
        livemode=payload["livemode"],
        created_at=parse_required_datetime(payload["created_at"]),
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
        created_at=parse_required_datetime(payload["created_at"]),
        reason=payload.get("reason"),
        description=payload.get("description"),
    )


def parse_charge_list(payload: Dict[str, Any]) -> ChargeList:
    return ChargeList(
        charges=[parse_charge(item) for item in payload.get("charges", [])],
        has_more=bool(payload.get("has_more")),
    )


def parse_payout(payload: Dict[str, Any]) -> Payout:
    return Payout(
        id=payload["id"],
        recipient_phone=payload["recipient_phone"],
        currency=payload["currency"],
        amount=payload["amount"],
        fee=payload["fee"],
        status=payload["status"],
        livemode=payload["livemode"],
        created_at=parse_required_datetime(payload["created_at"]),
        recipient_name=payload.get("recipient_name"),
        fail_reason=payload.get("fail_reason"),
        reference=payload.get("reference"),
        metadata=payload.get("metadata") or {},
        completed_at=parse_datetime(payload.get("completed_at")),
    )


def parse_payout_list(payload: Dict[str, Any]) -> PayoutList:
    return PayoutList(
        payouts=[parse_payout(item) for item in payload.get("payouts", [])],
        has_more=payload.get("has_more", False),
    )


def parse_event(payload: Dict[str, Any]) -> Event:
    data = payload.get("data") or {}
    charge = data.get("charge")
    refund = data.get("refund")
    payout = data.get("payout")

    # Parse only the object the event actually carries. Reading data["charge"]
    # unconditionally raised KeyError on every payout.* event.
    return Event(
        id=payload["id"],
        type=payload["type"],
        api_version=payload["api_version"],
        created_at=parse_required_datetime(payload["created_at"]),
        livemode=payload["livemode"],
        data=EventData(
            object=data.get("object", "charge"),
            charge=parse_charge(charge) if charge else None,
            refund=parse_refund(refund) if refund else None,
            payout=parse_payout(payout) if payout else None,
        ),
    )

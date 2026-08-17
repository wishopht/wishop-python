from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

CHARGE_STATUS_INITIATED = "INITIATED"
CHARGE_STATUS_OTP_SENT = "OTP_SENT"
CHARGE_STATUS_PAID = "PAID"
CHARGE_STATUS_FAILED = "FAILED"
CHARGE_STATUS_EXPIRED = "EXPIRED"
CHARGE_STATUS_REFUNDED = "REFUNDED"

FAIL_REASON_INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
FAIL_REASON_PIN_LOCKED = "PIN_LOCKED"
FAIL_REASON_OTP_EXPIRED = "OTP_EXPIRED"
FAIL_REASON_OTP_ATTEMPTS_EXCEEDED = "OTP_ATTEMPTS_EXCEEDED"
FAIL_REASON_WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
FAIL_REASON_DECLINED = "DECLINED"
FAIL_REASON_TIMEOUT = "TIMEOUT"
FAIL_REASON_INTERNAL_ERROR = "INTERNAL_ERROR"

FEE_BEARER_MERCHANT = "merchant"
FEE_BEARER_CUSTOMER = "customer"

REFUND_STATUS_PENDING = "pending"
REFUND_STATUS_SUCCEEDED = "succeeded"
REFUND_STATUS_FAILED = "failed"

REFUND_REASON_REQUESTED_BY_CUSTOMER = "requested_by_customer"
REFUND_REASON_DUPLICATE = "duplicate"
REFUND_REASON_FRAUDULENT = "fraudulent"
REFUND_REASON_OTHER = "other"

EVENT_CHARGE_PAID = "charge.paid"
EVENT_CHARGE_FAILED = "charge.failed"
EVENT_CHARGE_EXPIRED = "charge.expired"
EVENT_CHARGE_REFUNDED = "charge.refunded"


@dataclass(frozen=True)
class Charge:
    id: str
    status: str
    currency: str
    amount: str
    livemode: bool
    created_at: datetime
    order_id: Optional[str] = None
    description: Optional[str] = None
    fee_bearer: Optional[str] = None
    fee: Optional[str] = None
    net: Optional[str] = None
    customer_debit_amount: Optional[str] = None
    amount_refunded: Optional[str] = None
    customer_phone_masked: Optional[str] = None
    fail_reason: Optional[str] = None
    return_url: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    pay_url: Optional[str] = None


@dataclass(frozen=True)
class Refund:
    id: str
    charge: str
    amount: str
    currency: str
    status: str
    livemode: bool
    created_at: datetime
    reason: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class ChargeList:
    charges: List[Charge]
    has_more: bool


@dataclass(frozen=True)
class EventData:
    object: str
    charge: Charge
    refund: Optional[Refund] = None


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    api_version: str
    created_at: datetime
    livemode: bool
    data: EventData

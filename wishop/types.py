from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

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

EVENT_PAYOUT_CREATED = "payout.created"
EVENT_PAYOUT_SUCCEEDED = "payout.succeeded"
EVENT_PAYOUT_FAILED = "payout.failed"

PAYOUT_STATUS_PENDING = "PENDING"
PAYOUT_STATUS_SUCCEEDED = "SUCCEEDED"
PAYOUT_STATUS_FAILED = "FAILED"

# Payout-only fail reasons. FAIL_REASON_WALLET_NOT_FOUND is shared with charges.
FAIL_REASON_INSUFFICIENT_MERCHANT_BALANCE = "INSUFFICIENT_MERCHANT_BALANCE"
FAIL_REASON_RECIPIENT_INELIGIBLE = "RECIPIENT_INELIGIBLE"


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
class Payout:
    """Money sent from your wallet to a customer's.

    ``status`` of ``PAYOUT_STATUS_PENDING`` does not mean "queued": the wallet's
    answer was lost, so the money may or may not have moved. It resolves on its
    own and a ``payout.succeeded`` or ``payout.failed`` webhook reports the
    outcome. Never send a replacement payout for a pending one.
    """

    id: str
    recipient_phone: str
    currency: str
    amount: str
    # Charged on top of amount: your wallet is debited amount + fee.
    fee: str
    status: str
    livemode: bool
    created_at: datetime
    recipient_name: Optional[str] = None
    fail_reason: Optional[str] = None
    reference: Optional[str] = None
    # Values may be any JSON type, unlike a charge's string map.
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None


@dataclass(frozen=True)
class PayoutList:
    payouts: List[Payout]
    has_more: bool


@dataclass(frozen=True)
class EventData:
    """The object an event is about.

    ``object`` says which — ``"charge"`` on charge.* events, ``"payout"`` on
    payout.* ones — and only the matching field is set. ``charge`` became
    optional in 1.1.0: a payout event carries none, and reading it
    unconditionally used to raise KeyError.
    """

    object: str
    charge: Optional[Charge] = None
    refund: Optional[Refund] = None
    payout: Optional[Payout] = None


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    api_version: str
    created_at: datetime
    livemode: bool
    data: EventData

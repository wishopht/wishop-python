from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import List, Tuple, Union

from ._parsing import parse_event
from .errors import SignatureVerificationError
from .types import Event

DEFAULT_TOLERANCE = 300


def construct_event(
    payload: Union[bytes, str],
    signature_header: str,
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE,
) -> Event:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    timestamp, signatures = _parse_signature_header(signature_header)

    if tolerance > 0 and abs(time.time() - timestamp) > tolerance:
        raise SignatureVerificationError("timestamp outside the tolerance window")

    expected = hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("utf-8") + b"." + raw,
        hashlib.sha256,
    ).hexdigest()

    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise SignatureVerificationError("no signature matched the signing secret")

    try:
        decoded = json.loads(raw)
    except ValueError as exc:
        raise SignatureVerificationError("payload is not valid JSON") from exc

    return parse_event(decoded)


def _parse_signature_header(header: str) -> Tuple[int, List[str]]:
    timestamp = None
    signatures = []

    for part in header.split(","):
        key, separator, value = part.strip().partition("=")

        if not separator:
            continue

        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                raise SignatureVerificationError("malformed timestamp") from None
        elif key == "v1" and value:
            signatures.append(value)

    if timestamp is None:
        raise SignatureVerificationError("no timestamp in signature header")

    if not signatures:
        raise SignatureVerificationError("no v1 signature in signature header")

    return timestamp, signatures

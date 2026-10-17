from __future__ import annotations

from typing import Optional

import requests

from ._transport import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, Transport
from .resources.charges import Charges
from .resources.payouts import Payouts
from .resources.refunds import Refunds

VERSION = "1.2.0"


class Wishop:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        transport = Transport(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            user_agent="wishop-python/" + VERSION,
            session=session,
        )

        self.charges = Charges(transport)
        self.refunds = Refunds(transport)
        self.payouts = Payouts(transport)

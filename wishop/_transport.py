from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from .errors import APIConnectionError, error_for

DEFAULT_BASE_URL = "https://gatewayapi.wishopht.com"
DEFAULT_TIMEOUT = 30.0


class Transport:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        user_agent: str,
        session: Optional[requests.Session],
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._user_agent = user_agent
        self._session = session or requests.Session()

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        headers = {
            "Authorization": "Bearer " + self._api_key,
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        try:
            response = self._session.request(
                method,
                self._base_url + path,
                params=params or None,
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise APIConnectionError(str(exc)) from exc

        try:
            envelope = response.json()
        except ValueError:
            envelope = {}

        if not response.ok:
            message = envelope.get("message") or response.reason or "request failed"
            raise error_for(response.status_code, message, _retry_after(response))

        return envelope.get("data")


def _retry_after(response: requests.Response) -> Optional[int]:
    try:
        return int(response.headers["Retry-After"])
    except (KeyError, TypeError, ValueError):
        return None

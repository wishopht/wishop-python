from __future__ import annotations

from typing import Optional


class WishopError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(WishopError):
    pass


class AuthenticationError(WishopError):
    pass


class PermissionError(WishopError):
    pass


class NotFoundError(WishopError):
    pass


class ConflictError(WishopError):
    pass


class ChargeExpiredError(WishopError):
    pass


class PayloadTooLargeError(WishopError):
    pass


class UnprocessableError(WishopError):
    pass


class RateLimitError(WishopError):
    def __init__(self, message: str, status_code: int, retry_after: Optional[int] = None) -> None:
        super().__init__(message, status_code)
        self.retry_after = retry_after


class APIError(WishopError):
    pass


class APIConnectionError(WishopError):
    pass


class SignatureVerificationError(WishopError):
    pass


_BY_STATUS = {
    400: ValidationError,
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    409: ConflictError,
    410: ChargeExpiredError,
    413: PayloadTooLargeError,
    422: UnprocessableError,
}


def error_for(status_code: int, message: str, retry_after: Optional[int] = None) -> WishopError:
    if status_code == 429:
        return RateLimitError(message, status_code, retry_after)

    return _BY_STATUS.get(status_code, APIError)(message, status_code)

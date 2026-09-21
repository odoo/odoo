from http import HTTPStatus
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from odoo.tools.translate import LazyGettext

__all__ = [
    "AccessDenied",
    "AccessError",
    "CacheMiss",
    "ConcurrencyError",
    "LockError",
    "MissingError",
    "RedirectWarning",
    "RetryableJobError",
    "TerminalJobError",
    "UserError",
    "ValidationError",
]


class UserError(Exception):
    http_status: int = HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(self, message: str | LazyGettext) -> None:
        super().__init__(message)


class RedirectWarning(Exception):
    def __init__(
        self,
        message: str,
        action: int | str | dict,
        button_text: str,
        additional_context: dict | None = None,
    ) -> None:
        super().__init__(message, action, button_text, additional_context)


class AccessDenied(UserError):
    http_status: int = HTTPStatus.FORBIDDEN

    def __init__(self, message: str = "Access Denied") -> None:
        super().__init__(message)

    def suppress_traceback(self) -> None:
        self.with_traceback(None)
        self.__context__ = None
        self.__cause__ = None


class AccessError(UserError):
    http_status: int = HTTPStatus.FORBIDDEN


class _Named(Protocol):
    name: str


class CacheMiss(KeyError):
    def __init__(self, record: object, field: _Named) -> None:
        super().__init__("%r.%s" % (record, field.name))


class MissingError(UserError):
    http_status: int = HTTPStatus.NOT_FOUND


class LockError(UserError):
    http_status: int = HTTPStatus.CONFLICT


class ValidationError(UserError):
    pass


class ConcurrencyError(Exception):
    pass


class RetryableJobError(Exception):
    def __init__(self, message: str = "", seconds: int | None = None) -> None:
        super().__init__(message)
        self.seconds = seconds


class TerminalJobError(UserError):
    pass

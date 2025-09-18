"""HTTP layer exceptions."""

from http import HTTPStatus


class RegistryError(RuntimeError):
    """Error accessing the database registry."""


class SessionExpiredException(Exception):
    """The user session has expired."""

    http_status = HTTPStatus.FORBIDDEN

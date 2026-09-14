class CommError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(CommError):
    def __init__(
        self, message: str = "Authentication failed", status_code: int | None = None
    ):
        super().__init__(message, status_code)


class RateLimitError(CommError):
    def __init__(
        self, message: str = "Rate limit exceeded", status_code: int | None = None
    ):
        super().__init__(message, status_code)


class CommTimeoutError(CommError):
    def __init__(
        self, message: str = "Request timed out", status_code: int | None = None
    ):
        super().__init__(message, status_code)


class ClientError(CommError):
    def __init__(self, message: str = "Client error", status_code: int | None = None):
        super().__init__(message, status_code)


class ServerError(CommError):
    def __init__(self, message: str = "Server error", status_code: int | None = None):
        super().__init__(message, status_code)


class ValidationError(CommError):
    def __init__(
        self, message: str = "Validation error", status_code: int | None = None
    ):
        super().__init__(message, status_code)


class HostNotAllowedError(CommError):
    def __init__(
        self,
        message: str = "Host not allowed for this credential",
        status_code: int | None = None,
    ):
        super().__init__(message, status_code)

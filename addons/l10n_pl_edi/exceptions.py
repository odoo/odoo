from odoo.exceptions import UserError


class KSeFRateLimitError(UserError):

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = int(retry_after) if retry_after else None


class KSeFUnavailableError(UserError):
    """ KSeF could not be reached or failed on its side (connection error, timeout, 5xx answer). """


class KSeFTimeoutError(KSeFUnavailableError):
    pass

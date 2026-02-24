from odoo.exceptions import UserError


class KSeFRateLimitError(UserError):

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = int(retry_after) if retry_after else None

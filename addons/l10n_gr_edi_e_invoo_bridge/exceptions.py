from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class EInvooRequestError(Exception):
    def __init__(self, message=None):
        super().__init__(message or _lt("The electronic invoicing process could not be completed. Please retry later."))


class EInvooAuthenticationError(EInvooRequestError):
    def __init__(self):
        super().__init__(_lt("The Methodoos API token is invalid."))

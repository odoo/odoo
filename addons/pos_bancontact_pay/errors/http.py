from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


HTTP_ERRORS = {
    400: (
        _lt("The action could not be completed. Please try again or contact support."),
        MissingError,
    ),
    401: (
        _lt("Authentication with Bancontact failed. Please verify your API key."),
        AccessDenied,
    ),
    403: (
        _lt("Access denied. Please check your Bancontact permissions."),
        AccessDenied,
    ),
    404: (
        _lt("Merchant profile not found on Bancontact. Please check your Payment Profile ID (ppid)."),
        UserError,
    ),
    422: (
        _lt("Unable to process the request. Please verify your configuration or try again later."),
        ValidationError,
    ),
    429: (
        _lt("Rate limit reached with Bancontact. Please wait and try again."),
        AccessDenied,
    ),
    500: (
        _lt("Bancontact is currently unavailable. Please try again later."),
        AccessError,
    ),
    503: (
        _lt("Bancontact is currently unavailable. Please try again later."),
        AccessError,
    ),
}

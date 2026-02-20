from json import JSONDecodeError

from odoo import _
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)


def assert_bancontact_http_success(response, extra_errors=None):
    errors = {
        400: (
            _("The action could not be completed. Please try again or contact support."),
            MissingError,
        ),
        401: (
            _("Authentication with Bancontact failed. Please verify your API key."),
            AccessDenied,
        ),
        403: (
            _("Access denied. Please check your Bancontact permissions."),
            AccessDenied,
        ),
        404: (
            _("Merchant profile not found on Bancontact. Please check your Payment Profile ID (ppid)."),
            UserError,
        ),
        422: (
            _("Unable to process the request. Please verify your configuration or try again later."),
            ValidationError,
        ),
        429: (
            _("Rate limit reached with Bancontact. Please wait and try again."),
            AccessDenied,
        ),
        500: (
            _("Bancontact is currently unavailable. Please try again later."),
            AccessError,
        ),
        503: (
            _("Bancontact is currently unavailable. Please try again later."),
            AccessError,
        ),
        **(extra_errors or {}),
    }

    if response.status_code in errors:
        error_message, exception_class = errors[response.status_code]
        try:
            error_data = response.json()
        except JSONDecodeError:
            error_data = {}
        code = error_data.get("code", "")

        exception_msg = f"{error_message} (ERR: {response.status_code}"
        if code:
            exception_msg += f" - {code}"
        exception_msg += ")"
        raise exception_class(exception_msg)

    response.raise_for_status()

import logging
from json import JSONDecodeError

from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


def check_payconiq_http_status(response, errors):
    """
    Check the HTTP status of a Payconiq response and raise appropriate exceptions.

    :param response: The HTTP response object from the Payconiq API.
    :param errors: A dictionary mapping status codes to error messages and exception classes.
                   Example: {400: ("Bad Request", MissingError)}
    :raises: Corresponding Odoo exception based on the status code.
    """
    if response.status_code in errors:
        error_message, exception_class = errors[response.status_code]
        try:
            error_data = response.json()
            code = error_data.get("code", "")
            msg = error_data.get("message", "")

            log_msg = f"Payconiq error {response.status_code}: "
            if code:
                log_msg += f"{code} - "
            log_msg += f"{msg or error_message}"
            _logger.error(log_msg)

            exception_msg = f"{error_message} (ERR: {response.status_code}"
            if code:
                exception_msg += f" - {code}"
            exception_msg += ")"

            raise exception_class(exception_msg)

        except JSONDecodeError:
            _logger.exception("Failed to decode Payconiq JSON error response")
            msg = "Invalid response from Payconiq: unable to decode error message."
            raise AccessError(msg)

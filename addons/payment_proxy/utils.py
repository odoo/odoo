# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests

from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def send_api_request(method, url, *, params=None, data=None, json=None, headers=None, auth=None):
    """Send an HTTP request to a payment provider API and return the raw response.

    This utility handles the transport layer: it sends the request and raises
    :class:`~odoo.exceptions.ValidationError` on connection-level failures.  HTTP-level
    error handling (status codes, error-body parsing) is left to the caller so that
    each provider can apply its own response-parsing logic before raising.

    :param str method: The HTTP method (e.g. ``'GET'``, ``'POST'``).
    :param str url: The fully-qualified URL to send the request to.
    :param dict params: Query-string parameters to append to the URL.
    :param dict|str data: Form-encoded body of the request.
    :param dict json: JSON-encoded body of the request.
    :param dict headers: HTTP headers to include in the request.
    :param tuple auth: Basic-auth credentials as a ``(username, password)`` tuple.
    :return: The raw response object.
    :rtype: requests.Response
    :raise ValidationError: If a connection error or timeout occurs.
    """
    try:
        response = requests.request(
            method, url, params=params, data=data, json=json, headers=headers, auth=auth, timeout=10
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise ValidationError(
            _("Could not establish the connection to the payment provider.")
        ) from None

    return response

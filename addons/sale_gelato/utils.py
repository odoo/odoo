import logging

import requests

from odoo import _
from odoo.exceptions import UserError
from odoo.libs import guarded_http, netguard
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def send_request(api_key, subdomain, version, endpoint, payload=None, method="POST"):
    url = f"https://{subdomain}.gelatoapis.com/{version}/{endpoint}"
    _debug.pipeline("gelato_request", endpoint=endpoint, method=method)
    headers = {"X-API-KEY": api_key or None}
    body = {"params": payload} if method in ("GET", "DELETE") else {"json": payload}
    try:
        with guarded_http.guarded_session(netguard.PUBLIC_ONLY) as session:
            response = session.request(method, url, headers=headers, timeout=10, **body)
        response_content = response.json()
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            _debug.logic(
                "gelato_request_rejected",
                endpoint=endpoint,
                status=response.status_code,
            )
            _logger.exception("Invalid API request at %s with data %s", url, payload)
            raise UserError(response_content.get("message", "")) from error
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
        _debug.logic(
            "gelato_request_unreachable",
            endpoint=endpoint,
            error=type(error).__name__,
        )
        _logger.exception("Unable to reach endpoint at %s", url)
        raise UserError(
            _("Could not establish the connection to the Gelato API.")
        ) from error
    return response.json()

import functools
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import urlparse, parse_qsl

from odoo import tools
from odoo.addons.hw_drivers.tools import helpers
from odoo.http import request
from werkzeug.exceptions import Forbidden

_logger = logging.getLogger(__name__)
WINDOW = 5


def protect(endpoint):
    """Decorate a route to protect it with a hmac signature. If the IoT Box is not connected
    to a db, the route will not be protected.
    """
    fname = f"<function {endpoint.__module__}.{endpoint.__qualname__}>"

    @functools.wraps(endpoint)
    def protect_wrapper(*args, **kwargs):
        # If no db connected, we don't protect the endpoint
        if not helpers.get_odoo_server_url():
            return endpoint(*args, **kwargs)

        signature = request.httprequest.headers.get('Authorization')
        url = request.httprequest.url
        payload = dict(kwargs)
        if not signature or not verify_hmac_signature(url, payload, signature):
            _logger.error('%s: Authentication failed.', fname)
            return Forbidden('Authentication failed.')

        return endpoint(*args, **kwargs)
    return protect_wrapper


def hmac_sign(url, payload, t=None):
    """Compute HMAC signature for the url and the payload of a request with
    the IoT Box `token` as key.

    :param url: url of the request
    :param payload: payload of the request
    :param float t: timestamp to use for the signature, if not provided, the current
        time is used
    :return: HMAC signature of the timestamp, url and payload
    """
    if not t:
        t = time.time()

    parsed_url = urlparse(url)
    query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))

    payload = "%s|%s|%s|%s" % (
        int(t),
        parsed_url.path,
        json.dumps(query_params, sort_keys=True),
        json.dumps(payload, sort_keys=True),
    )
    return hmac.new(helpers.get_token().encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_hmac_signature(url, payload, signature, t=None, window=WINDOW):
    """Verify the signature of a payload.

    :param url: url of the request
    :param payload: payload of the request
    :param signature: signature to verify
    :param float t: timestamp to use for the signature, if not provided, the
        current time is used
    :param int window: fuzz window to account for slow fingers, network
        latency, desynchronised clocks, ..., every signature valid between
        t-window and t+window is considered valid
    """
    if not t:
        t = time.time()

    low = int(t - window)
    high = int(t + window)

    return next((
        counter for counter in range(low, high)
        if tools.consteq(signature, hmac_sign(url, payload, counter))
    ), None)

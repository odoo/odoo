import hashlib
import hmac
import json
import time
from urllib.parse import urlparse, parse_qsl

from odoo import tools

WINDOW = 5


def hmac_sign(url, payload, token, t=None):
    """Compute HMAC signature for the url and the payload of a request with
    the IoT Box `token` as key.

    :param url: url of the request
    :param payload: payload of the request
    :param token: token to use for the signature
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
    return hmac.new(token.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_hmac_signature(url, payload, signature, token, t=None, window=WINDOW):
    """Verify the signature of a payload.

    :param url: url of the request
    :param payload: payload of the request
    :param signature: signature to verify
    :param token: token to use for the signature
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
        if tools.consteq(signature, hmac_sign(url, payload, token, counter))
    ), None)

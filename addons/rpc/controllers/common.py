import logging
from collections import OrderedDict

from odoo.http import request

RPC_DEPRECATION_NOTICE = """\
The /xmlrpc and /xmlrpc/2 endpoints are deprecated in Odoo 19 \
and scheduled for removal in Odoo 20. Please report the problem to the \
client making the request: %s, %s.
Mute this logger: --log-handler %s:ERROR
https://www.odoo.com/documentation/latest/developer/reference/external_api.html#migrating-from-xml-rpc-json-rpc"""

# Ordered so the oldest entry can be evicted once the cache is full: a plain
# `set` at its cap would latch permanently silent for every new caller too,
# not just the ones already warned.
_WARNED_CLIENTS: OrderedDict[tuple[str, str, str], None] = OrderedDict()

_WARNED_CLIENTS_LIMIT = 64


def warn_endpoint_is_deprecated(logger: logging.Logger, module: str) -> None:
    client = request.httprequest.remote_addr or "unknown"
    agent = request.httprequest.user_agent.string or "no user-agent"
    key = (module, client, agent)
    if key in _WARNED_CLIENTS:
        return
    if len(_WARNED_CLIENTS) >= _WARNED_CLIENTS_LIMIT:
        _WARNED_CLIENTS.popitem(last=False)
    _WARNED_CLIENTS[key] = None
    logger.warning(RPC_DEPRECATION_NOTICE, client, agent, module)


def detach_database() -> None:
    if request.db:
        request.detach_database()

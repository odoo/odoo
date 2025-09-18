"""HTTP utility functions."""

import logging
import re
import threading
import traceback
from urllib.parse import quote as url_quote

import psycopg

import odoo.service.common
import odoo.service.db
import odoo.service.model
from odoo.tools import config

from .constants import SESSION_LIFETIME
from .core import borrow_request

_logger = logging.getLogger(__name__)


def content_disposition(filename, disposition_type="attachment"):
    """
    Craft a ``Content-Disposition`` header, see :rfc:`6266`.

    :param filename: The name of the file, should that file be saved on
        disk by the browser.
    :param disposition_type: Tell the browser what to do with the file,
        either ``"attachment"`` to save the file on disk,
        either ``"inline"`` to display the file.
    """
    if disposition_type not in ("attachment", "inline"):
        e = f"Invalid disposition_type: {disposition_type!r}"
        raise ValueError(e)
    return f"{disposition_type}; filename*=UTF-8''{url_quote(filename, safe='')}"


def db_list(force=False, host=None):
    """
    Get the list of available databases.

    :param bool force: See :func:`~odoo.service.db.list_dbs`:
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: the list of available databases
    :rtype: list[str]
    """
    try:
        dbs = odoo.service.db.list_dbs(force)
    except psycopg.OperationalError:
        return []
    return db_filter(dbs, host)


def db_filter(dbs, host=None):
    """
    Return the subset of ``dbs`` that match the dbfilter or the dbname
    server configuration. In case neither are configured, return ``dbs``
    as-is.

    :param Iterable[str] dbs: The list of database names to filter.
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: The original list filtered.
    :rtype: list[str]
    """
    from . import (
        request,
    )

    if config["dbfilter"]:
        #        host
        #     -----------
        # www.example.com:80
        #     -------
        #     domain
        if host is None:
            host = request.httprequest.environ.get("HTTP_HOST", "")
        host = host.partition(":")[0]
        host = host.removeprefix("www.")
        domain = host.partition(".")[0]

        dbfilter_re = re.compile(
            config["dbfilter"]
            .replace("%h", re.escape(host))
            .replace("%d", re.escape(domain))
        )
        return [db for db in dbs if dbfilter_re.match(db)]

    if config["db_name"]:
        # In case --db-filter is not provided and --database is passed, Odoo will
        # use the value of --database as a comma separated list of exposed databases.
        return sorted(set(config["db_name"]).intersection(dbs))

    return list(dbs)


def _get_rpc_dispatcher(service_name):
    """Resolve RPC dispatcher lazily to avoid circular imports."""
    match service_name:
        case "common":
            return odoo.service.common.dispatch
        case "db":
            return odoo.service.db.dispatch
        case "object":
            return odoo.service.model.dispatch
        case _:
            raise KeyError(service_name)


def dispatch_rpc(service_name, method, params):
    """
    Perform a RPC call.

    :param str service_name: either "common", "db" or "object".
    :param str method: the method name of the given service to execute
    :param Mapping params: the keyword arguments for method call
    :return: the return value of the called method
    :rtype: Any
    """
    with borrow_request():
        threading.current_thread().uid = None
        threading.current_thread().dbname = None

        dispatch = _get_rpc_dispatcher(service_name)
        return dispatch(method, params)


def get_session_max_inactivity(env):
    """Get the maximum session inactivity time in seconds."""
    if not env or env.cr._closed:
        return SESSION_LIFETIME

    ICP = env["ir.config_parameter"].sudo()

    try:
        return int(ICP.get_param("sessions.max_inactivity_seconds", SESSION_LIFETIME))
    except ValueError:
        _logger.warning(
            "Invalid value for 'sessions.max_inactivity_seconds', using default value."
        )
        return SESSION_LIFETIME
    except psycopg.Error:
        # The database connection may have been terminated (e.g. the
        # database was just dropped).  Fall back to the default lifetime
        # instead of crashing the request.
        _logger.debug(
            "Could not read session max inactivity from DB, using default.",
            exc_info=True,
        )
        return SESSION_LIFETIME


def is_cors_preflight(request, endpoint):
    """Check if the request is a CORS preflight request."""
    return request.httprequest.method == "OPTIONS" and endpoint.routing.get(
        "cors", False
    )


def serialize_exception(exception, *, message=None, arguments=None):
    """Serialize an exception for JSON response."""
    name = type(exception).__name__
    module = type(exception).__module__

    return {
        "name": f"{module}.{name}" if module else name,
        "message": str(exception) if message is None else message,
        "arguments": exception.args if arguments is None else arguments,
        "context": getattr(exception, "context", {}),
        "debug": "".join(traceback.format_exception(exception)),
    }

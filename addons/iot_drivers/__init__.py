# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import wraps

import requests

from . import (
    connection_manager,
    controllers,
    event_manager,
    exception_logger,
    http,
    interface,
    iot_handlers,
    main,
    server_logger,
    tools,
    websocket_client,
)

for interface_thread in main.interfaces.values():
    interface_thread().start()

_get = requests.get
_post = requests.post


def set_default_options(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        headers = kwargs.pop("headers", None) or {}
        headers["User-Agent"] = "OdooIoTBox/1.0"
        server_url = tools.helpers.get_odoo_server_url()
        db_name = tools.system.get_conf("db_name")
        if (
            server_url
            and db_name
            and args[0].startswith(server_url)
            and "/web/login?db=" not in args[0]
        ):
            headers["X-Odoo-Database"] = db_name
        return func(*args, headers=headers, **kwargs)

    return wrapper


requests.get = set_default_options(_get)
requests.post = set_default_options(_post)

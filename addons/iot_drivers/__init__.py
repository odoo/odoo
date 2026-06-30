# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import wraps
import requests
import logging

from . import server_logger
from . import connection_manager
from . import controllers
from . import driver
from . import event_manager
from . import exception_logger
from . import http
from . import interface
from . import main
from . import tools
from . import websocket_client
from . import webrtc_client

_logger = logging.getLogger(__name__)
_logger.warning("==== Starting Odoo ====")

_get = requests.get
_post = requests.post


def set_default_options(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        headers = kwargs.pop('headers', None) or {}
        headers['User-Agent'] = 'OdooIoTBox/1.0'
        server_url = tools.helpers.get_odoo_server_url()
        db_name = tools.helpers.get_conf('db_name')
        if server_url and db_name and args[0].startswith(server_url) and '/web/login?db=' not in args[0]:
            headers['X-Odoo-Database'] = db_name
        return func(*args, headers=headers, **kwargs)

    return wrapper


requests.get = set_default_options(_get)
requests.post = set_default_options(_post)

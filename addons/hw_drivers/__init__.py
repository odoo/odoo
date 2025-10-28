# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cryptography.x509 import Certificate
from functools import wraps
import platform
import requests

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

_get = requests.get
_post = requests.post


def set_user_agent(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        headers = kwargs.pop('headers', None) or {}
        headers['User-Agent'] = 'OdooIoTBox/1.0'
        return func(*args, headers=headers, **kwargs)

    return wrapper


requests.get = set_user_agent(_get)
requests.post = set_user_agent(_post)

# Ensure cryptography compatibility with python < 3.13
if platform.system() == 'Linux' and float(tools.helpers.get_version()[1:8]) < 2025.10:
    Certificate.not_valid_after_utc = Certificate.not_valid_after

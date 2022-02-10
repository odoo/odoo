# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from . import db
from . import model
from . import server

import logging
import threading

#.apidoc title: RPC Services

""" Classes of this module implement the network protocols that the
    OpenERP server uses to communicate with remote clients.

    Some classes are mostly utilities, whose API need not be visible to
    the average user/developer. Study them only if you are about to
    implement an extension to the network protocols, or need to debug some
    low-level behavior of the wire.
"""

_dispatchers = {
    'common': common.dispatch,
    'db': db.dispatch,
    'object': model.dispatch,
}

def dispatch_rpc(service_name, method, params):
    """ Handle a RPC call.

    This is pure Python code, the actual marshalling (from/to XML/JSON)
    is done in a upper layer.
    """
    threading.current_thread().uid = None
    threading.current_thread().dbname = None

    dispatch = _dispatchers[service_name]

    return dispatch(method, params)

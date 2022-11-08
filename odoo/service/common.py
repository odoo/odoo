# -*- coding: utf-8 -*-

import logging

import odoo.release
import odoo.tools
from odoo.exceptions import AccessDenied
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

RPC_VERSION_1 = {
        'server_version': odoo.release.version,
        'server_version_info': odoo.release.version_info,
        'server_serie': odoo.release.serie,
        'protocol_version': 1,
}


ODOO18_DEPRECATION_WARNING = """
The %r service was deprecated in Odoo 7 (more than 10 years ago)
and does nothing since then. This service is scheduled for removal in
Odoo 18 but one of your clients is still using it, please report them
this current warning. If they desire to keep on using a no-op function,
they can use the 'version' service."""


def exp_login(db, login, password):
    return exp_authenticate(db, login, password, None)

def exp_authenticate(db, login, password, user_agent_env):
    if not user_agent_env:
        user_agent_env = {}
    res_users = odoo.registry(db)['res.users']
    try:
        return res_users.authenticate(db, login, password, {**user_agent_env, 'interactive': False})
    except AccessDenied:
        return False

def exp_version():
    return RPC_VERSION_1

def exp_about(extended=False):
    """Return information about the OpenERP Server.

    @param extended: if True then return version info
    @return string if extended is False else tuple
    """
    _logger.warning(ODOO18_DEPRECATION_WARNING, "about")

    info = _('See http://openerp.com')

    if extended:
        return info, odoo.release.version
    return info

def exp_set_loglevel(loglevel, logger=None):
    _logger.warning(ODOO18_DEPRECATION_WARNING, "set_loglevel")
    return True

def dispatch(method, params):
    g = globals()
    exp_method_name = 'exp_' + method
    if exp_method_name in g:
        return g[exp_method_name](*params)
    else:
        raise Exception("Method not found: %s" % method)

# -*- coding: utf-8 -*-

import logging

import odoo.release
import odoo.tools
from odoo.exceptions import AccessDenied
from odoo.modules.registry import Registry
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

def exp_login(db, login, password):
    return exp_authenticate(db, login, password, None)

def exp_authenticate(db, login, password, user_agent_env):
    if not user_agent_env:
        user_agent_env = {}
    with Registry(db).cursor() as cr:
        env = odoo.api.Environment(cr, None, {})
        env.transaction.default_env = env  # force default_env
        try:
            credential = {'login': login, 'password': password, 'type': 'password'}
            return env['res.users'].authenticate(credential, {**user_agent_env, 'interactive': False})['uid']
        except AccessDenied:
            return False

def dispatch(method, params):
    g = globals()
    exp_method_name = 'exp_' + method
    if exp_method_name in g:
        return g[exp_method_name](*params)
    else:
        raise Exception("Method not found: %s" % method)

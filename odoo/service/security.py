# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.exceptions

def login(db, login, password):
    res_users = odoo.registry(db)['res.users']
    return res_users._login(db, login, password)

def check(db, uid, passwd):
    res_users = odoo.registry(db)['res.users']
    return res_users.check(db, uid, passwd)

def compute_session_token(session, env):
    self = env['res.users'].browse(session.uid)
    return self._compute_session_token(session.sid)

def check_session(session, env):
    self = env['res.users'].browse(session.uid)
    if odoo.tools.misc.consteq(self._compute_session_token(session.sid), session.session_token):
        return True
    self._invalidate_session_cache()
    return False

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.modules.registry import Registry
from odoo.tools.misc import consteq


def check(db, uid, passwd):
    res_users = Registry(db)['res.users']
    return res_users.check(db, uid, passwd)


def compute_session_token(session, env):
    self = env['res.users'].browse(session.uid)
    return self._compute_session_token(session.sid)


def check_session(session, env, request=None):
    self = env['res.users'].browse(session.uid)
    expected = self._compute_session_token(session.sid)
    if expected:
        if consteq(expected, session.session_token):
            if request:
                env['res.device.log']._update_device(request)
            return True
        # If the session token is not valid, we check if the legacy version works
        # and convert the session token to the new one
        legacy_expected = self._legacy_session_token_hash_compute(session.sid)
        if legacy_expected and consteq(legacy_expected, session.session_token):
            session.session_token = expected
            if request:
                env['res.device.log']._update_device(request)
            return True
    return False

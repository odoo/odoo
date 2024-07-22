# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
from hashlib import sha256
from functools import lru_cache, wraps

import odoo
import odoo.exceptions


def lru_cache_ignoring_first_argument(func):
    first = None

    @lru_cache
    def _cached(*args):
        return func(first, *args)

    @wraps(func)
    def wrapper(*args):
        nonlocal first
        first, *rest = args
        return _cached(*rest)

    wrapper.cache_clear = _cached.cache_clear
    return wrapper


SESSION_TOKEN_FIELDS = {"id", "login", "password", "active"}


def check(db, uid, passwd):
    res_users = odoo.registry(db)['res.users']
    return res_users.check(db, uid, passwd)


@lru_cache_ignoring_first_argument
def compute_session_token_with_cr(cr, sid, uid):
    session_fields = ", ".join(sorted(SESSION_TOKEN_FIELDS))
    cr.execute(
        """SELECT %s, (SELECT value FROM ir_config_parameter WHERE key='database.secret')
                            FROM res_users
                            WHERE id=%%s"""
        % (session_fields),
        (uid,),
    )
    if cr.rowcount != 1:
        return False
    data_fields = cr.fetchone()
    # generate hmac key
    key = ("%s" % (data_fields,)).encode("utf-8")
    # hmac the session id
    data = sid.encode("utf-8")
    h = hmac.new(key, data, sha256)
    # keep in the cache the token
    return h.hexdigest()


def compute_session_token(session, env):
    return compute_session_token_with_cr(env.cr, session.sid, session.uid)


def check_session_with_cr(session, cr):
    expected = compute_session_token_with_cr(cr, session.sid, session.uid)
    if expected and odoo.tools.misc.consteq(expected, session.session_token):
        return True
    return False


def check_session(session, env):
    return check_session_with_cr(session, env.cr)


def clear_session_cache():
    compute_session_token_with_cr.cache_clear()

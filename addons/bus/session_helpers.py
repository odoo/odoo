import hashlib
import hmac
import time

from odoo.api import Environment
from odoo.modules.registry import Registry
from odoo.sql_db import SQL
from odoo.tools.lru import LRU
from odoo.tools.misc import consteq

_query_params_by_user = LRU(8192)


def _get_session_token_query_params(cr, session):
    """
    Retrieve the session token query parameters like
    `res.users@_get_session_token_query_params`, but with caching to avoid building the
    full registry. The cache is invalidated when `registry.registry_sequence` has changed.
    """
    cache_key = (cr.dbname, session.uid)
    if cached_value := _query_params_by_user.get(cache_key):
        cr.execute('SELECT MAX(id) FROM orm_signaling_registry')
        if cached_value['registry_sequence'] == cr.fetchone()[0]:
            return cached_value['query_params']
    Registry(cr.dbname).check_signaling()
    env = new_env(cr, session)
    params = env.user._get_session_token_query_params()
    _query_params_by_user[cache_key] = {
        'registry_sequence': env.registry.registry_sequence,
        'query_params': params,
    }
    return params


def check_session(cr, session):
    session._delete_old_sessions()
    if 'deletion_time' in session and session['deletion_time'] <= time.time():
        return False
    query_params = _get_session_token_query_params(cr, session)
    cr.execute(
        SQL(
            'SELECT %(select)s FROM %(from)s %(joins)s WHERE %(where)s GROUP BY %(group_by)s',
            **query_params,
        ),
    )
    if cr.rowcount != 1:
        return False
    row = cr.fetchone()
    key_tuple = tuple(
        (col.name, row[i]) for i, col in enumerate(cr.description) if row[i] is not None
    )
    key = str(key_tuple).encode()
    token = hmac.new(key, session.sid.encode(), hashlib.sha256).hexdigest()
    return consteq(token, session.session_token)


def new_env(cr, session, *, set_lang=False):
    """
    Create a new environment. Make sure the transaction has a `default_env` and
    if requested, set the language of the user in the context.
    """
    uid = session.uid
    ctx = dict(session.context, lang=None)  # lang is not guaranteed to be correct
    env = Environment(cr, uid, ctx)
    if set_lang:
        lang = env['res.lang']._get_code(ctx['lang'])
        env = env(context=dict(ctx, lang=lang))
    if not env.transaction.default_env:
        env.transaction.default_env = env
    return env

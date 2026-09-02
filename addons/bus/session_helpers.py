import hashlib
import hmac
import os
import time
import typing

from odoo.api import SUPERUSER_ID, Environment
from odoo.http.session import session_store
from odoo.sql_db import SQL
from odoo.tools.lru import LRU
from odoo.tools.misc import consteq

if typing.TYPE_CHECKING:
    from odoo.http.session import Session
    OldSID = typing.NewType("OldSID", str)
    ResolvedSession = typing.NewType("ResolvedSession", Session)

# The session-token query has a registry level shape (SELECT/FROM/JOIN/GROUP BY)
# and a per user WHERE (`res_users.id = <uid>`).
_query_params_by_dbname = LRU(8192)

# Last seen (mtime, inode) of each sid's session file. `SessionStore.save()` always
# rewrites via a fresh mkstemp+os.replace. Inode is used to tiebreak two writes that would
# land on the same mtime.
_stat_by_sid = LRU(8192)


def _get_session_token_query_params(cr, uids):
    """
    Retrieve the session token query parameters like
    `res.users@_get_session_token_query_params`, but with caching to avoid building the
    full registry. The cache is invalidated when `registry.registry_sequence` has changed.

    Only the registry level shape is cached (`SELECT`/`FROM`/`JOIN`/`GROUP BY`) as it is
    common to all users. The `WHERE` clause is added according to ``uids``.
    """
    where = SQL("res_users.id IN %s", tuple(uids))
    if cached := _query_params_by_dbname.get(cr.dbname):
        cr.execute("SELECT MAX(id) FROM orm_signaling_registry")
        if cached["registry_sequence"] == cr.fetchone()[0]:
            return {**cached["query_params"], "where": where}
    env = Environment(cr, SUPERUSER_ID, {})
    params = env["res.users"]._get_session_token_query_params()
    # assert params["where"]` is SQL("res_users.id = %s", False)
    # `TestWebsocketCheckSession.test_query_shape_is_user_agnostic`.
    params.pop("where", None)
    _query_params_by_dbname[cr.dbname] = {
        "query_params": params,
        "registry_sequence": env.registry.registry_sequence,
    }
    return {**params, "where": where}


def check_sessions(cr, sessions):
    """Counterpart of ``odoo.http.session.check`` that must not build a registry.

    Verify that the sessions are not expired and that the token saved in each one
    still matches the session token computed for its user.

    :param sessions: the sessions to check.
    :returns: valid sessions, keyed by the ``sid`` that was given. That key differs from
        the checked session's ``sid`` when a rotation happened.
    """
    store = session_store()
    now = time.time()
    resolved_by_sid: dict[OldSID, ResolvedSession] = {}
    to_check_by_sid = {}
    for stored_session in sessions:
        if stored_session.sid in resolved_by_sid or stored_session.sid in to_check_by_sid:
            continue
        if stored_session.uid is None:
            resolved_by_sid[stored_session.sid] = stored_session  # No user, no token to match.
            continue
        try:
            # Open instead of stat (close to open consistency): NFS clients cache file
            # attributes for seconds (acregmin/acregmax) which could hide a delete from
            # another node sharing `session_dir`. Opening forces a revalidation.
            with open(store.get_session_path(stored_session.sid), "rb", buffering=0) as f:
                st = os.fstat(f.fileno())
                session_stat = (st.st_mtime_ns, st.st_ino)
        except (OSError, ValueError):
            continue  # Session wasn't found on disk (= outdated).
        if _stat_by_sid.get(stored_session.sid) == session_stat:
            stored = stored_session  # Unchanged since last check.
        else:
            stored = store.get(stored_session.sid)
            if stored.is_new:
                continue  # Session wasn't found on disk (= outdated).
            _stat_by_sid[stored_session.sid] = session_stat
        if "next_sid" in stored:
            stored = store.get(stored["next_sid"])
            if stored.is_new:
                continue
        store.delete_old_sessions(stored)
        if "deletion_time" in stored and stored["deletion_time"] <= now:
            continue
        to_check_by_sid[stored_session.sid] = stored
    if not to_check_by_sid:
        return resolved_by_sid
    uids = {session.uid for session in to_check_by_sid.values()}
    query_params = _get_session_token_query_params(cr, uids)
    cr.execute(
        SQL(
            "SELECT %(select)s FROM %(from)s %(joins)s WHERE %(where)s GROUP BY %(group_by)s",
            **query_params,
        ),
    )
    id_idx = next(i for i, column in enumerate(cr.description) if column.name == "id")
    keys_by_uid = {}
    # Mirror `_session_token_get_values` then `_session_token_hash_compute`.
    for row in cr.fetchall():
        field_values = tuple(
            (column.name, row[index]) for index, column in enumerate(cr.description)
        )
        key_tuple = tuple((k, v) for k, v in field_values if v is not None)
        keys_by_uid[row[id_idx]] = str(key_tuple).encode()

    for given_sid, stored_session in to_check_by_sid.items():
        key = keys_by_uid.get(stored_session.uid)
        if not key:
            continue
        token = hmac.new(key, stored_session.sid.encode(), hashlib.sha256).hexdigest()
        if consteq(token, stored_session.session_token):
            resolved_by_sid[given_sid] = stored_session
    return resolved_by_sid


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

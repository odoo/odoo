import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest
from werkzeug.test import EnvironBuilder

from odoo.http._session_store import (
    FilesystemSessionStore,
    MemorySessionStore,
    PostgresSessionStore,
)
from odoo.http.constants import prepare_default_session
from odoo.http.exceptions import SessionExpiredException
from odoo.http.request_class import Request
from odoo.http.session import Session
from odoo.http.wrappers import HTTPRequest, Response
from odoo.libs.func import Callbacks


@pytest.fixture(params=["filesystem", "memory", "postgres"])
def store(request, tmp_path):
    if request.param == "memory":
        return MemorySessionStore(Session)
    if request.param == "postgres":
        dbname = os.environ.get("ODOO_HTTP_SESSION_TEST_DB")
        if not dbname:
            pytest.skip("set ODOO_HTTP_SESSION_TEST_DB to a scratch database")
        assert dbname
        pg_store = PostgresSessionStore(dbname, Session)
        pg_store.clear()
        return pg_store
    return FilesystemSessionStore(str(tmp_path), Session)


def saved_session(store):
    session = store.new()
    session.update(prepare_default_session())
    store.save(session)
    return session


@pytest.mark.parametrize("operation", ["save", "keep_alive", "rotate"])
def test_a_revoked_session_cannot_be_recreated(store, operation):
    session = saved_session(store)
    stale = store.get(session.sid)
    store.delete(session)
    stale.mark_dirty()
    with pytest.raises(SessionExpiredException):
        if operation == "rotate":
            store.rotate(stale, None)
        else:
            getattr(store, operation)(stale)
    assert store.get(session.sid).is_new


def test_a_late_keep_alive_after_logout_cannot_restore_authentication(store):
    session = saved_session(store)
    session.uid = 7
    session.session_token = "valid-for-the-old-cookie"
    store.save(session)
    stale = store.get(session.sid)
    session.logout()
    store.rotate(session, None)
    with pytest.raises(SessionExpiredException):
        store.keep_alive(stale)
    assert store.get(stale.sid).is_new


def test_logout_revokes_the_whole_soft_rotation_chain(store):
    session = saved_session(store)
    first_sid = session.sid
    store.rotate(session, None, soft=True)
    second_sid = session.sid
    stale = store.get(first_sid)
    store.stage_rotation(stale, None, soft=True)
    session.logout()
    store.rotate(session, None)
    assert store.get(first_sid).is_new
    assert store.get(second_sid).is_new
    with pytest.raises(SessionExpiredException):
        store.rotate(stale, None, soft=True)


def test_soft_rotation_preserves_a_peers_independent_change(store):
    session = saved_session(store)
    rotating, peer = store.get(session.sid), store.get(session.sid)
    rotating["own_change"] = 1
    peer["peer_change"] = 2
    store.save(peer)
    store.rotate(rotating, None, soft=True)
    saved = store.get(rotating.sid)
    assert saved["own_change"] == 1
    assert saved["peer_change"] == 2


@pytest.mark.parametrize("staged", [False, True])
def test_soft_rotation_rejects_a_missing_successor(store, staged):
    session = saved_session(store)
    stale = store.get(session.sid)
    if staged:
        store.stage_rotation(stale, None, soft=True)
    store.rotate(session, None, soft=True)
    store.delete(session)
    with pytest.raises(SessionExpiredException):
        store.rotate(stale, None, soft=True)


def test_concurrent_disjoint_changes_survive(store):
    original = saved_session(store)
    sessions = [store.get(original.sid) for _ in range(16)]

    def save_one(index):
        if not isinstance(store, FilesystemSessionStore):
            pytest.skip("a second process sharing the store is a filesystem case")
        peer_store = FilesystemSessionStore(store.path, Session)
        sessions[index][f"key_{index}"] = index
        peer_store.save(sessions[index])

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(save_one, range(len(sessions))))
    current = store.get(original.sid)
    assert {current[f"key_{i}"] for i in range(16)} == set(range(16))


def test_a_deletion_does_not_remove_a_peers_unrelated_change(store):
    original = saved_session(store)
    original["remove_me"] = True
    store.save(original)
    first, second = store.get(original.sid), store.get(original.sid)
    first["keep_me"] = True
    del second["remove_me"]
    store.save(first)
    store.save(second)
    assert "remove_me" not in store.get(original.sid)
    assert store.get(original.sid)["keep_me"] is True


def test_disjoint_nested_context_changes_survive(store):
    original = saved_session(store)
    first, second = store.get(original.sid), store.get(original.sid)
    first.context["lang"] = "es_MX"
    second.context["tz"] = "America/Mexico_City"
    store.save(first)
    store.save(second)
    assert store.get(original.sid).context == {
        "lang": "es_MX",
        "tz": "America/Mexico_City",
    }


@pytest.mark.parametrize("soft", [False, True])
def test_failed_rotation_restores_in_memory_identity(store, monkeypatch, soft):
    session = saved_session(store)
    session.should_rotate = True
    original = session.snapshot()

    def fail(session):
        raise OSError("disk full")

    monkeypatch.setattr(store, "_save_unlocked", fail)
    with pytest.raises(OSError):
        store.rotate(session, None, soft)
    assert session.sid == original.sid
    assert dict(session) == dict(original)
    assert session.should_rotate
    assert session.rotation is None
    assert not store.get(original.sid).is_new


def test_vacuum_never_removes_lock_inodes(store):
    session = saved_session(store)
    if not isinstance(store, FilesystemSessionStore):
        pytest.skip("lock stripes are the filesystem store's")
    lock_path = Path(store.path, ".locks", session.sid[:2])
    inode = lock_path.stat().st_ino
    old = time.time() - 1000
    os.utime(lock_path, (old, old))
    store.vacuum(max_lifetime=1)
    assert lock_path.stat().st_ino == inode


@pytest.mark.parametrize("suffix", ["\n", "\r", " ", "/"])
def test_session_keys_require_an_exact_match(store, suffix):
    assert not store.is_valid_key(store.generate_key() + suffix)


def transaction_request(store):
    session = saved_session(store)
    req: Any = Request(
        HTTPRequest(EnvironBuilder().get_environ()),
        SimpleNamespace(
            session_store=store, update_standard_headers=lambda response: None
        ),
    )
    req.session = store.get(session.sid)
    req.db = None
    cursor = SimpleNamespace(
        closed=False, postcommit=Callbacks(), postrollback=Callbacks()
    )
    req.env = SimpleNamespace(cr=cursor)
    req._bind_session_transaction(cursor)
    return req, cursor


def test_session_changes_are_published_only_after_commit(store):
    req, cursor = transaction_request(store)
    req.session["effect"] = 1
    response = Response("ok")
    req.dispatcher.post_dispatch(response)
    assert "effect" not in store.get(req.session.sid)
    assert not response.headers.getlist("Set-Cookie")
    cursor.postcommit.run()
    assert store.get(req.session.sid)["effect"] == 1
    assert response.headers.getlist("Set-Cookie")


def test_rollback_discards_session_changes_and_pending_rotation(store):
    req, cursor = transaction_request(store)
    sid = req.session.sid
    req.session["effect"] = 1
    req.session.should_rotate = True
    req._save_session()
    reserved_sid = req.session.sid
    assert reserved_sid != sid
    assert store.get(reserved_sid).is_new
    cursor.postcommit.clear()
    cursor.postrollback.run()
    assert req.session.sid == sid
    assert "effect" not in req.session
    assert not store.get(sid).is_new
    assert store.get(reserved_sid).is_new


def test_reserved_rotation_is_the_identity_published_at_commit(store):
    req, cursor = transaction_request(store)
    old_sid = req.session.sid
    req.session.should_rotate = True
    req._save_session()
    reserved_sid = req.session.sid
    response = Response(reserved_sid)
    req.dispatcher.post_dispatch(response)
    assert req.session.sid == reserved_sid
    assert not store.get(old_sid).is_new
    cursor.postcommit.run()
    assert store.get(old_sid).is_new
    assert not store.get(reserved_sid).is_new
    assert reserved_sid in response.headers["Set-Cookie"]


def test_failed_request_does_not_reenable_session_persistence(store):
    req, cursor = transaction_request(store)
    req.session.can_save = False
    cursor.postcommit.clear()
    cursor.postrollback.run()
    assert not req.session.can_save


def test_an_internal_rollback_does_not_disable_post_commit_persistence(store):
    req, cursor = transaction_request(store)
    cursor.postcommit.clear()
    cursor.postrollback.run()
    req.session["effect"] = 1
    response = Response("ok")
    req.dispatcher.post_dispatch(response)
    assert "effect" not in store.get(req.session.sid)
    cursor.postcommit.run()
    assert store.get(req.session.sid)["effect"] == 1
    assert response.headers.getlist("Set-Cookie")


def test_rollback_restore_is_deterministic_between_the_participant_and_the_cursor(
    store,
):
    from odoo.http._retry import RequestRetryParticipant

    req, cursor = transaction_request(store)
    sid = req.session.sid
    req.session["effect"] = 1
    req.session.can_save = False

    RequestRetryParticipant(req).on_rollback(Exception("promoted"))
    assert "effect" not in req.session
    assert not req.session.can_save, "a refusal to save survives the restore"
    assert req._session_snapshot is not None, "armed until commit or a rebind"

    req.session["late"] = 2
    cursor.postrollback.run()
    assert "late" not in req.session, "every restore lands on the bound state"
    assert req.session.sid == sid


def test_a_handler_rollback_then_a_retry_still_restores_the_bound_state(store):
    from odoo.http._retry import RequestRetryParticipant

    req, cursor = transaction_request(store)
    cursor.postrollback.run()
    req.session["after_internal_rollback"] = 1
    RequestRetryParticipant(req).on_rollback(Exception("serialization"))
    assert "after_internal_rollback" not in req.session


def test_a_rotation_persisted_through_an_explicit_env_survives_the_rollback(store):
    from odoo.http._retry import RequestRetryParticipant

    req, cursor = transaction_request(store)
    req.session["login"] = "alice"
    cookie_sid = req.session.sid
    foreign_env = SimpleNamespace(cr=SimpleNamespace(closed=False))

    req.session.should_rotate = True
    req._save_session(foreign_env)
    rotated_sid = req.session.sid
    assert rotated_sid != cookie_sid
    assert store.get(cookie_sid).is_new, "a hard rotation removed the old file"

    cursor.postrollback.run()
    RequestRetryParticipant(req).on_rollback(Exception("serialization"))
    assert req.session.sid == rotated_sid
    assert not store.get(req.session.sid).is_new, "the replay can still save"
    assert req.session["login"] == "alice"


def test_a_committed_session_can_no_longer_be_restored(store):
    req, cursor = transaction_request(store)
    req.session["effect"] = 1
    req.dispatcher.post_dispatch(Response("ok"))
    cursor.postcommit.run()
    assert req._session_snapshot is None

    req._restore_session_snapshot()
    assert req.session["effect"] == 1


def test_a_disk_reload_on_rollback_does_not_reselect_the_database(store):
    from odoo import http

    req, _cursor = transaction_request(store)
    req.db = "served_db"
    req.session.db = "served_db"
    req.httprequest = SimpleNamespace(
        session_id=req.session.sid,
        remote_addr=None,
        environ={"HTTP_HOST": "h"},
        headers={"X-Odoo-Database": "other_db"},
        accept_languages=SimpleNamespace(best=None),
    )
    store.save(req.session)
    req._session_written_in_transaction = True

    with (
        mock.patch.object(http, "filter_dbs_served") as filtered,
        mock.patch.object(http, "get_dbs_served") as listed,
    ):
        req._restore_session_snapshot()

    assert req.session.db == "served_db"
    assert filtered.call_count == 0, "the restore consulted the dbfilter"
    assert listed.call_count == 0

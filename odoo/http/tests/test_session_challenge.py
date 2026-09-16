"""Regression contracts from the session and cookie correctness challenge."""

import os
from types import SimpleNamespace

import pytest

from odoo.http._cookies import get_cookie_identity
from odoo.http._session_store import (
    FilesystemSessionStore,
    MemorySessionStore,
    PostgresSessionStore,
)
from odoo.http.constants import prepare_default_session
from odoo.http.exceptions import SessionExpiredException
from odoo.http.session import Session
from odoo.http.wrappers import Response


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


def token_env():
    return {
        "res.users": SimpleNamespace(
            browse=lambda uid: SimpleNamespace(
                _get_session_token=lambda sid: f"{uid}:{sid}"
            )
        )
    }


def authenticated(store):
    session = store.new()
    session.update(prepare_default_session(), uid=7, login="user")
    session.session_token = f"7:{session.sid}"
    store.save(session)
    return session


def test_logout_after_staging_soft_rotation_revokes_original(store):
    session = authenticated(store)
    original_sid = session.sid
    store.stage_rotation(session, token_env(), soft=True)
    session.logout()
    store.rotate(session, token_env())
    assert store.get(original_sid).is_new
    assert session.sid[:42] != original_sid[:42]
    assert store.get(session.sid).uid is None


@pytest.mark.parametrize("rotations", [1, 3])
def test_late_predecessor_save_reaches_the_live_successor(store, rotations):
    session = authenticated(store)
    late = store.get(session.sid)
    for _ in range(rotations):
        store.rotate(session, token_env(), soft=True)
    late["cart"] = 42
    store.save(late)
    assert store.get(session.sid).get("cart") == 42
    assert late.sid == session.sid
    assert late.session_token == f"{late.uid}:{late.sid}"


@pytest.mark.parametrize("operation", ["save", "rotate"])
def test_adoption_cannot_mix_different_users(store, operation):
    session = authenticated(store)
    late = store.get(session.sid)
    original_sid = late.sid
    store.rotate(session, token_env(), soft=True)
    session.uid = 8
    session.session_token = f"8:{session.sid}"
    store.save(session)
    late["cart"] = 42
    with pytest.raises(SessionExpiredException, match="identity changed"):
        if operation == "save":
            store.save(late)
        else:
            store.rotate(late, token_env(), soft=True)
    assert late.sid == original_sid
    assert "cart" not in store.get(session.sid)


@pytest.mark.parametrize("foreign_family", [False, True])
def test_rotation_chain_must_stay_acyclic_and_in_one_family(store, foreign_family):
    session = authenticated(store)
    session["next_sid"] = store.new().sid if foreign_family else session.sid
    store.save(session)
    with pytest.raises(SessionExpiredException, match="rotation chain"):
        store.rotate(store.get(session.sid), token_env(), soft=True)


def test_concurrent_identity_update_and_soft_rotation_keep_token_consistent(store):
    session = authenticated(store)
    rotating = store.get(session.sid)
    store.stage_rotation(rotating, token_env(), soft=True)
    session.uid = 8
    session.session_token = f"8:{session.sid}"
    store.save(session)
    store.rotate(rotating, token_env(), soft=True)
    assert rotating.session_token == f"{rotating.uid}:{rotating.sid}"


@pytest.mark.parametrize("operation", ["save", "rotate"])
def test_failed_peer_adoption_restores_identity(store, monkeypatch, operation):
    session = authenticated(store)
    late = store.get(session.sid)
    original_sid = late.sid
    store.rotate(session, token_env(), soft=True)
    late["cart"] = 42

    def fail(session):
        raise OSError("write failed")

    monkeypatch.setattr(store, "_save_unlocked", fail)
    with pytest.raises(OSError):
        if operation == "save":
            store.save(late)
        else:
            store.rotate(late, None, soft=True)
    assert late.sid == original_sid
    assert late["cart"] == 42
    assert late.session_token == f"7:{original_sid}"


def test_cookie_extension_attributes_do_not_change_scope_parsing():
    assert get_cookie_identity("a=1; Priority=High; Path=/one") == (
        "a",
        "",
        "/one",
        False,
    )


def test_cookie_opaque_extension_does_not_collapse_distinct_scopes():
    response = Response(
        headers=[
            ("Set-Cookie", "a=1; Priority=High; Path=/one"),
            ("Set-Cookie", "a=2; Priority=High; Path=/two"),
        ]
    )
    response.set_cookie("a", "3", path=None)
    assert len(response.headers.getlist("Set-Cookie")) == 3


def test_normal_hard_logout_control(store):
    session = authenticated(store)
    original_sid = session.sid
    session.logout()
    store.rotate(session, None)
    assert store.get(original_sid).is_new
    assert store.get(session.sid).uid is None


def test_normal_soft_rotation_token_control(store):
    session = authenticated(store)
    store.rotate(session, token_env(), soft=True)
    assert store.get(session.sid).session_token == f"7:{session.sid}"


def test_independent_edits_before_rotation_control(store):
    session = authenticated(store)
    peer = store.get(session.sid)
    peer["cart"] = 42
    store.save(peer)
    store.rotate(session, token_env(), soft=True)
    assert store.get(session.sid)["cart"] == 42

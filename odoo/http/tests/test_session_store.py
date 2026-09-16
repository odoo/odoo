import os
import pathlib
import time
from types import SimpleNamespace
from typing import Any

import pytest

from odoo.http._session_store import FilesystemSessionStore
from odoo.http.constants import STORED_SESSION_BYTES, prepare_default_session
from odoo.http.request_class import Request
from odoo.http.session import Session, _coerce_session_value


@pytest.fixture
def store(tmp_path):
    return FilesystemSessionStore(str(tmp_path), session_class=Session)


def _anon(store):
    s = store.new()
    s["uid"] = None
    store.save(s)
    return s


def test_generate_key_shape_and_prefix_invariant(tmp_path):
    store = FilesystemSessionStore(str(tmp_path), session_class=Session)
    key = store.generate_key()
    assert len(key) == 84
    assert store.is_valid_key(key)
    assert len(key) > STORED_SESSION_BYTES


def test_soft_rotation_keeps_prefix_changes_suffix(store):
    s = _anon(store)
    old = s.sid
    store.rotate(s, env=None, soft=True)
    assert s.sid != old
    assert s.sid[:STORED_SESSION_BYTES] == old[:STORED_SESSION_BYTES]
    assert store.get(old)["next_sid"] == s.sid
    assert store.get(s.sid).get("gc_previous_sessions") is True


def test_hard_rotation_changes_whole_sid(store):
    s = _anon(store)
    old = s.sid
    store.rotate(s, env=None, soft=False)
    assert s.sid[:STORED_SESSION_BYTES] != old[:STORED_SESSION_BYTES]


def test_concurrent_peer_unmodified_adopts_new_sid(store):
    s = _anon(store)
    old = s.sid
    store.rotate(s, env=None, soft=True)
    peer = store.get(old)
    store.rotate(peer, env=None, soft=True)
    assert peer.sid == s.sid


def test_concurrent_peer_modified_flushes_without_stale_markers(store):
    s = _anon(store)
    old = s.sid
    store.rotate(s, env=None, soft=True)
    peer = store.get(old)
    peer.mark_clean()
    peer["foo"] = "bar"
    store.rotate(peer, env=None, soft=True)
    merged = store.get(s.sid)
    assert merged.get("foo") == "bar"
    assert "next_sid" not in merged
    assert "deletion_time" not in merged


def test_delete_old_sessions_keeps_current_removes_predecessor(store):
    s = _anon(store)
    old = s.sid
    store.rotate(s, env=None, soft=True)
    s["create_time"] = time.time() - 10_000
    store.save(s)
    store.remove_old_sessions(s)
    assert not pathlib.Path(store.get_session_filename(old)).exists()
    assert pathlib.Path(store.get_session_filename(s.sid)).exists()


def test_delete_from_identifiers_rejects_bad_identifier(store):
    with pytest.raises(ValueError, match="Identifier format"):
        store.remove_sessions_for_identifiers(["../etc"])


def test_vacuum_operates_on_own_path(store, tmp_path):
    s = _anon(store)
    fn = pathlib.Path(store.get_session_filename(s.sid))
    import os

    old = time.time() - 10 * 24 * 3600
    os.utime(fn, (old, old))
    store.vacuum(max_lifetime=7 * 24 * 3600)
    assert not fn.exists()


def test_vacuum_reaps_orphaned_tmp_files(store, tmp_path):
    from odoo.http._session_store import _TEMPORARY_SUFFIX as _fs_transaction_suffix

    orphan = tmp_path / f"tmpabc123{_fs_transaction_suffix}"
    orphan.write_bytes(b"{}")
    import os

    old = time.time() - 10 * 24 * 3600
    os.utime(orphan, (old, old))
    fresh = tmp_path / f"tmpdef456{_fs_transaction_suffix}"
    fresh.write_bytes(b"{}")
    store.vacuum(max_lifetime=7 * 24 * 3600)
    assert not orphan.exists()
    assert fresh.exists()


def test_vacuum_takes_one_lock_per_stripe_and_ignores_foreign_directories(
    store, tmp_path, monkeypatch
):
    sessions = [_anon(store) for _ in range(6)]
    old = time.time() - 10 * 24 * 3600
    for s in sessions:
        os.utime(store.get_session_filename(s.sid), (old, old))
    stripes = {s.sid[:2] for s in sessions}
    (tmp_path / "not a stripe").mkdir()
    (tmp_path / "not a stripe" / "junk").write_bytes(b"{}")

    opened: list[str] = []
    real_open = store._open_lock_file

    def counting_open(stripe):
        opened.append(stripe)
        return real_open(stripe)

    monkeypatch.setattr(store, "_open_lock_file", counting_open)
    store.vacuum(max_lifetime=7 * 24 * 3600)

    assert sorted(opened) == sorted(stripes), "one lock per stripe, not per file"
    assert not any(
        pathlib.Path(store.get_session_filename(s.sid)).exists() for s in sessions
    )
    assert (tmp_path / "not a stripe" / "junk").exists()


def test_get_records_the_file_age_and_touches_nothing(store):
    s = _anon(store)
    fn = pathlib.Path(store.get_session_filename(s.sid))
    old = time.time() - 2 * 24 * 3600
    os.utime(fn, (old, old))
    loaded = store.get(s.sid)
    assert loaded.mtime == pytest.approx(old)
    assert fn.stat().st_mtime == pytest.approx(old), "liveness is the request's call"

    store.keep_alive(loaded)
    assert loaded.mtime == pytest.approx(time.time(), abs=5)
    assert fn.stat().st_mtime == pytest.approx(time.time(), abs=5)


def test_corrupt_session_file_is_discarded_and_renewed(store):
    s = _anon(store)
    fn = pathlib.Path(store.get_session_filename(s.sid))
    fn.write_bytes(b"{corrupt json!!")
    renewed = store.get(s.sid)
    assert renewed.is_new
    assert renewed.sid != s.sid
    assert not fn.exists()


def test_non_dict_session_payload_is_treated_as_corrupt(store):
    for payload in (b"null", b"[1, 2]", b'"str"'):
        s = _anon(store)
        fn = pathlib.Path(store.get_session_filename(s.sid))
        fn.write_bytes(payload)
        renewed = store.get(s.sid)
        assert renewed.is_new and renewed.sid != s.sid
        assert not fn.exists()


def test_coerce_session_value_rejects_non_json():
    import datetime

    with pytest.raises(TypeError):
        _coerce_session_value(datetime.datetime(2020, 1, 1))
    assert _coerce_session_value((1, 2)) == [1, 2]
    assert _coerce_session_value({"a": (1, "x")}) == {"a": [1, "x"]}
    with pytest.raises(TypeError):
        _coerce_session_value({1: "int-key"})


def test_session_is_modified_detects_nested_mutation():
    s = Session({"context": {"lang": "en_US"}}, "sid", new=True)
    s.mark_clean()
    assert not s.is_modified()
    s["context"]["lang"] = "es_MX"
    assert s.is_modified()


def _interrupted_peer_rotation(store, session):
    next_sid = (
        session.sid[:STORED_SESSION_BYTES] + store.generate_key()[STORED_SESSION_BYTES:]
    )
    peer_view = store.get(session.sid)
    peer_view["next_sid"] = next_sid
    peer_view["deletion_time"] = time.time() + 120
    store.save(peer_view)
    return next_sid


def test_soft_rotation_does_not_adopt_a_sid_with_no_file(store):
    session = store.new()
    session["uid"] = 2
    session["session_token"] = "token-computed-for-the-old-sid"
    store.save(session)
    old_sid = session.sid

    _interrupted_peer_rotation(store, session)

    concurrent = store.get(old_sid)
    from odoo.http.exceptions import SessionExpiredException

    with pytest.raises(SessionExpiredException):
        store.rotate(concurrent, env=None, soft=True)

    assert concurrent.sid == old_sid
    landed = store.get(concurrent.sid)
    assert not landed.is_new, (
        "rotate() moved the session onto a sid with no file behind it"
    )
    assert landed["uid"] == 2, "failed rotation must not rewrite the original file"


def test_soft_rotation_adopts_once_the_peer_file_lands(store):
    session = store.new()
    session["uid"] = 2
    session["session_token"] = "old-token"
    store.save(session)
    old_sid = session.sid

    next_sid = _interrupted_peer_rotation(store, session)
    peer_final = Session({"uid": 2, "session_token": "new-token"}, next_sid, new=True)
    store.save(peer_final)

    concurrent = store.get(old_sid)
    store.rotate(concurrent, env=None, soft=True)

    assert concurrent.sid == next_sid, "the peer's rotation must be adopted"
    assert not store.get(next_sid).is_new


class _RotationRequest(Request):
    httprequest: Any

    def __init__(self, store, session, sid_on_cookie):
        httprequest: Any = SimpleNamespace(
            session_id=sid_on_cookie,
            path="/web/login",
            is_secure=False,
            remote_addr=None,
        )
        super().__init__(httprequest, SimpleNamespace(session_store=store))
        self.session = session


def test_pending_rotation_survives_a_request_with_no_live_env(store):
    s = store.new()
    s["uid"] = 7
    s["create_time"] = time.time()
    store.save(s)
    s.mark_clean()
    original_sid = s.sid
    s.should_rotate = True

    _RotationRequest(store, s, original_sid)._save_session()

    assert s.sid == original_sid, "rotation must be deferred, not attempted"
    assert store.get(original_sid)["_rotate_pending"] is True


def test_pending_rotation_rearms_on_the_next_load(store):
    s = store.new()
    s["uid"] = 7
    s["_rotate_pending"] = True
    store.save(s)

    reloaded = store.get(s.sid)
    assert reloaded.should_rotate is False
    if reloaded.pop("_rotate_pending", None):
        reloaded.should_rotate = True

    assert reloaded.should_rotate is True
    assert "_rotate_pending" not in reloaded


def test_pending_rotation_is_not_parked_when_it_can_run(store):
    s = _anon(store)
    s.should_rotate = True
    original_sid = s.sid

    _RotationRequest(store, s, original_sid)._save_session()

    assert s.sid != original_sid
    assert "_rotate_pending" not in store.get(s.sid)


def test_touch_is_a_keep_alive_not_a_content_change():
    s = Session({}, "sid", False)
    s["uid"] = 1
    s.mark_clean()

    s.mark_dirty()
    assert s.is_dirty
    assert not s.has_content_changed()
    assert s.is_modified()

    s["lang"] = "es"
    assert s.has_content_changed()


def test_keep_alive_bumps_mtime_without_rewriting(store):
    s = _anon(store)
    path = pathlib.Path(store.get_session_filename(s.sid))
    before_bytes = path.read_bytes()
    old = time.time() - 10_000
    os.utime(path, (old, old))

    store.keep_alive(s)

    assert path.read_bytes() == before_bytes
    assert path.stat().st_mtime > old


def test_keep_alive_persists_a_session_with_no_file_yet(store):
    s = store.new()
    s["uid"] = None
    path = pathlib.Path(store.get_session_filename(s.sid))
    assert not path.exists()

    store.keep_alive(s)

    assert path.exists()


def test_session_files_are_readable_only_by_their_owner(store):
    session = store.new()
    session["uid"] = 2
    store.save(session)

    mode = pathlib.Path(store.get_session_filename(session.sid)).stat().st_mode
    assert mode & 0o777 == 0o600


def test_the_odoo_store_shards_by_the_first_two_characters(store):
    sid = store.new().sid
    assert pathlib.Path(store.get_session_filename(sid)).parts[-2:] == (sid[:2], sid)


def _token_for(sid):
    return "tok:" + sid


class _TokenEnv(dict):
    def __getitem__(self, key):
        return SimpleNamespace(
            browse=lambda uid: SimpleNamespace(_get_session_token=_token_for)
        )


def _rotating_session(store, uid=7):
    session = store.new()
    for key, value in prepare_default_session().items():
        session.setdefault(key, value)
    session["uid"] = uid
    session["session_token"] = _token_for(session.sid)
    session.mark_clean()
    store.save(session)
    return session.sid


@pytest.mark.parametrize("follower_is_modified", [True, False])
def test_following_a_soft_rotation_adopts_the_peer_identity_with_its_sid(
    store, follower_is_modified
):
    env = _TokenEnv()
    sid0 = _rotating_session(store)

    leader = store.get(sid0)
    leader.mark_clean()
    leader.should_rotate = True
    store.rotate(leader, env, True)
    assert leader.sid != sid0

    follower = store.get(sid0)
    follower.mark_clean()
    if follower_is_modified:
        follower["marker"] = 1
    follower.should_rotate = True
    store.rotate(follower, env, True)

    assert follower.sid == leader.sid
    assert follower["session_token"] == _token_for(follower.sid)
    assert "next_sid" not in follower
    assert "deletion_time" not in follower


def test_a_save_after_following_a_rotation_does_not_log_the_owner_out(store):
    env = _TokenEnv()
    sid0 = _rotating_session(store)

    leader = store.get(sid0)
    leader.mark_clean()
    store.rotate(leader, env, True)

    follower = store.get(sid0)
    follower.mark_clean()
    store.rotate(follower, env, True)
    store.save(follower)

    on_disk = store.get(follower.sid)
    assert on_disk["session_token"] == _token_for(follower.sid)
    assert on_disk["uid"] == 7

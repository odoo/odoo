import time
import types
from typing import Any

import pytest

from odoo.http import _session_lifecycle, request_class
from odoo.http.constants import SESSION_LIFETIME, SESSION_ROTATION_INTERVAL


class _Store:
    def __init__(self, fail=False):
        self.calls: list[str] = []
        self.fail = fail

    def _record(self, name):
        self.calls.append(name)
        if self.fail:
            raise OSError("disk full")

    def rotate(self, session, env, soft=False):
        self._record("rotate_soft" if soft else "rotate")

    def save(self, session):
        self._record("save")

    def keep_alive(self, session):
        self._record("keep_alive")


class _Session(dict):
    def __init__(self, **kw):
        super().__init__({"create_time": time.time(), **kw})
        self.sid = kw.pop("sid", "S" * 84)
        self.can_save = True
        self.is_dirty = False
        self.is_new = False
        self.should_rotate = False
        self.mtime = None
        self._content_changed = False

    @property
    def uid(self):
        return self.get("uid")

    def has_content_changed(self):
        return self._content_changed


class _Cookies:
    def __init__(self):
        self.set: dict[str, Any] = {}

    def set_cookie(self, key, value, **kw):
        self.set[key] = (value, kw)


MAX_INACTIVITY = 4242


@pytest.fixture(autouse=True)
def _fixed_inactivity(monkeypatch):
    monkeypatch.setattr(
        _session_lifecycle, "get_session_max_inactivity", lambda env: MAX_INACTIVITY
    )


def _save(session, *, store=None, env="open", cookie_sid=None, path="/x"):
    store = store or _Store()
    if env == "open":
        env = types.SimpleNamespace(cr=types.SimpleNamespace(closed=False))
    elif env == "closed":
        env = types.SimpleNamespace(cr=types.SimpleNamespace(closed=True))
    future = _Cookies()
    httprequest: Any = types.SimpleNamespace(
        remote_addr=None, session_id=cookie_sid, path=path
    )
    this: Any = request_class.Request(
        httprequest, app=types.SimpleNamespace(session_store=store)
    )
    this.session = session
    this.env = env
    this.future_response = future
    this._persist_session(env)
    return store, future


def test_a_session_that_may_not_be_saved_is_not_touched_at_all():
    s = _Session()
    s.can_save = False
    s.should_rotate = True
    store, future = _save(s)
    assert store.calls == []
    assert future.set == {}


def test_a_rotation_with_a_live_cursor_rotates():
    s = _Session(uid=2)
    s.should_rotate = True
    store, future = _save(s)
    assert store.calls == ["rotate"]
    assert "session_id" in future.set


def test_a_rotation_without_a_cursor_is_deferred_not_lost():
    s = _Session(uid=2)
    s.should_rotate = True
    store, _ = _save(s, env="closed")
    assert store.calls == ["save"]
    assert s["_rotate_pending"] is True


def test_an_anonymous_session_can_always_rotate():
    s = _Session()
    s.should_rotate = True
    store, _ = _save(s, env=None)
    assert store.calls == ["rotate"]


def test_an_old_authenticated_session_rotates_softly():
    s = _Session(uid=2)
    s["create_time"] = time.time() - SESSION_ROTATION_INTERVAL - 1
    store, _ = _save(s)
    assert store.calls == ["rotate_soft"]


def test_the_periodic_rotation_skips_excluded_paths(monkeypatch):
    monkeypatch.setattr(
        _session_lifecycle, "SESSION_ROTATION_EXCLUDED_PATHS", {"/poll"}
    )
    s = _Session(uid=2)
    s["create_time"] = time.time() - SESSION_ROTATION_INTERVAL - 1
    store, _ = _save(s, path="/poll")
    assert store.calls == []


def test_changed_content_is_written():
    s = _Session(uid=2)
    s._content_changed = True
    store, _ = _save(s)
    assert store.calls == ["save"]


def test_a_dirty_but_unchanged_session_is_only_touched():
    s = _Session(uid=2)
    s.is_dirty = True
    store, _ = _save(s)
    assert store.calls == ["keep_alive"]


def test_a_new_dirty_session_is_written_not_touched():
    s = _Session()
    s.is_new = True
    s.is_dirty = True
    store, future = _save(s)
    assert store.calls == ["save"], "a file that does not exist yet cannot be touched"
    assert "session_id" in future.set


@pytest.mark.parametrize(
    ("uid", "budget"), [(2, MAX_INACTIVITY), (None, SESSION_LIFETIME)]
)
def test_a_session_past_half_its_budget_is_kept_alive_with_a_fresh_cookie(uid, budget):
    s = _Session(uid=uid)
    s.mtime = time.time() - budget / 2 - 1
    store, future = _save(s)
    assert store.calls == ["keep_alive"], "nothing changed, only the file age"
    assert future.set["session_id"][1]["max_age"] == budget, (
        "the browser's cookie lifetime is extended along with the file's"
    )


def test_a_session_inside_half_its_budget_is_left_alone():
    s = _Session(uid=2)
    s.mtime = time.time() - MAX_INACTIVITY / 2 + 60
    store, future = _save(s, cookie_sid=s.sid)
    assert store.calls == []
    assert future.set == {}


def test_an_untouched_session_costs_nothing_and_sets_no_cookie():
    s = _Session(uid=2)
    store, future = _save(s, cookie_sid="S" * 84)
    assert store.calls == []
    assert future.set == {}


def test_a_new_session_that_was_never_written_gets_no_cookie():
    s = _Session()
    s.is_new = True
    store, future = _save(s)
    assert store.calls == []
    assert future.set == {}


def test_a_failed_write_keeps_the_current_cookie():
    s = _Session(uid=2)
    s._content_changed = True
    store, future = _save(s, store=_Store(fail=True))
    assert store.calls == ["save"]
    assert future.set == {}, "a cookie for a session that is not on disk"


def test_a_changed_sid_sets_the_cookie_even_when_nothing_else_moved():
    s = _Session(uid=2)
    store, future = _save(s, cookie_sid="D" * 84)
    assert store.calls == []
    assert future.set["session_id"][0] == s.sid


@pytest.mark.parametrize(
    ("uid", "expected"), [(None, SESSION_LIFETIME), (2, MAX_INACTIVITY)]
)
def test_the_cookie_lifetime_follows_authentication(uid, expected):
    s = _Session(**({"uid": uid} if uid else {}))
    s._content_changed = True
    _, future = _save(s)
    assert future.set["session_id"][1]["max_age"] == expected


def test_an_error_response_keeps_the_budget_read_while_the_cursor_was_live():
    s = _Session(uid=2)
    s._content_changed = True
    store = _Store()
    future = _Cookies()
    httprequest: Any = types.SimpleNamespace(
        remote_addr=None, session_id=None, path="/x"
    )
    this: Any = request_class.Request(
        httprequest, app=types.SimpleNamespace(session_store=store)
    )
    this.session = s
    this.future_response = future
    this.env = types.SimpleNamespace(cr=types.SimpleNamespace(closed=False))
    this._persist_session(this.env)
    assert future.set["session_id"][1]["max_age"] == MAX_INACTIVITY

    this.env = None
    this._persist_session(None)
    assert future.set["session_id"][1]["max_age"] == MAX_INACTIVITY, (
        "the error path has no environment; the cookie must not fall back to "
        "SESSION_LIFETIME once the real budget was read"
    )


def test_without_any_live_environment_the_budget_is_the_default():
    s = _Session(uid=2)
    s._content_changed = True
    _, future = _save(s, env=None)
    assert future.set["session_id"][1]["max_age"] == SESSION_LIFETIME

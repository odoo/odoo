import types
from typing import Any
from unittest import mock

import psycopg
import pytest
import werkzeug.datastructures

from odoo.http import _serve
from odoo.http.request_class import Request
from odoo.libs.worker_thread import current_worker_thread


class _Cursor:
    def __init__(self, readonly):
        self.readonly = readonly
        self.closed = False
        self.rollbacks = 0
        self.commit_count = 0

    def close(self):
        self.closed = True

    def rollback(self):
        self.rollbacks += 1


class _Env:
    def __init__(self, cr, registry):
        self.cr = cr
        self.registry = registry
        self.rebound_to = None

    def __call__(self, cr=None, **kw):
        self.rebound_to = cr
        return self


def _serve_db(this):
    return this._serve_db()


def _make(readonly_route=True, replica=True):
    calls: dict[str, Any] = {"served": 0, "reset_for_replay": [], "opened": []}
    first = _Cursor(readonly=replica)

    endpoint = types.SimpleNamespace(
        routing={"readonly": readonly_route, "type": "http"},
        func=types.SimpleNamespace(__self__=object()),
    )
    rule = types.SimpleNamespace(endpoint=endpoint)

    def _cursor(readonly=False, pin_key=None):
        cr = _Cursor(readonly=False)
        calls["opened"].append(cr)
        return cr

    class _Registry:
        db_name = "db"

        def __init__(self):
            self.cursor = _cursor

        def __getitem__(self, name):
            return types.SimpleNamespace(_match=lambda path: (rule, {}))

    registry = _Registry()
    env = _Env(first, registry)

    httprequest: Any = types.SimpleNamespace(
        remote_addr=None,
        method="GET",
        path="/x",
        files=werkzeug.datastructures.MultiDict(),
    )
    this: Any = Request(httprequest, app=None)
    this.db = "db"
    this.registry = registry
    this.session = types.SimpleNamespace(uid=1, context={}, sid="S" * 84)
    this._acquire_registry_cursor = lambda: first
    this._update_dispatcher = lambda r: None
    this._serve_ir_http = lambda r, a: "served"
    this._update_served_exception = lambda exc: None
    this._bind_session_transaction = lambda cr: None
    this._flush_session = lambda: None
    this._reset_for_replay = lambda cr=None: calls["reset_for_replay"].append(cr)

    this.calls = calls
    this.first_cursor = first
    return this, env


@pytest.fixture(autouse=True)
def _clean_thread():
    current_worker_thread().cursor_mode = None
    yield
    current_worker_thread().cursor_mode = None


def _run(this, env, retrying_side_effect):
    with (
        mock.patch.object(_serve.odoo.api, "Environment", return_value=env),
        mock.patch.object(_serve, "retrying", side_effect=retrying_side_effect),
    ):
        return _serve_db(this)


def test_without_a_replica_a_readonly_route_runs_read_write():
    this, env = _make(readonly_route=True, replica=False)
    served = _run(this, env, lambda func, env, participant=None: func())

    assert served == "served"
    assert current_worker_thread().cursor_mode == "rw"
    assert this.first_cursor.rollbacks == 1, (
        "the cursor must be rolled back, not reopened"
    )
    assert this.calls["opened"] == [], "no second cursor is opened without a replica"
    assert this.calls["reset_for_replay"] == []


def test_with_a_replica_a_readonly_route_stays_on_the_readonly_cursor():
    this, env = _make(readonly_route=True, replica=True)
    served = _run(this, env, lambda func, env, participant=None: func())

    assert served == "served"
    assert current_worker_thread().cursor_mode == "ro"
    assert this.first_cursor.rollbacks == 0
    assert this.calls["opened"] == []


def test_a_write_from_a_readonly_route_is_promoted_and_replayed():
    this, env = _make(readonly_route=True, replica=True)
    attempts = []

    def retrying(func, env, participant=None):
        attempts.append(1)
        if len(attempts) == 1:
            raise psycopg.errors.ReadOnlySqlTransaction("cannot execute UPDATE ")
        return func()

    with mock.patch.object(_serve, "RequestRetryParticipant") as participant:
        participant.return_value.on_retry.side_effect = lambda exc: (
            this._reset_for_replay()
        )
        served = _run(this, env, retrying)

    assert served == "served"
    assert len(attempts) == 2, "the handler must run a second time"
    assert current_worker_thread().cursor_mode == "ro->rw"
    assert this.first_cursor.closed, "the readonly cursor must be closed"
    assert len(this.calls["opened"]) == 1, "a read/write cursor must be opened"
    assert this.calls["reset_for_replay"] == this.calls["opened"], (
        "the replay must rebuild the environment on the NEW cursor, and only "
        "on it -- an extra reset here binds an Environment to the read-only "
        "cursor the next line closes"
    )
    participant.assert_called_once_with(this)
    instance = participant.return_value
    assert instance.on_rollback.called, "the session is reloaded before the replay"
    assert not instance.on_retry.called, (
        "on_retry resets against the doomed read-only cursor; _serve_db resets "
        "against the read/write one it opens"
    )


def test_a_promotion_rewinds_the_uploaded_files_before_the_replay():
    this, env = _make(readonly_route=True, replica=True)
    upload = mock.Mock()
    upload.seekable.return_value = True
    this.httprequest.files = werkzeug.datastructures.MultiDict({"f": upload})
    attempts = []

    def retrying(func, env, participant=None):
        attempts.append(1)
        if len(attempts) == 1:
            raise psycopg.errors.ReadOnlySqlTransaction("cannot execute UPDATE ")
        return func()

    with mock.patch.object(_serve, "RequestRetryParticipant"):
        assert _run(this, env, retrying) == "served"

    upload.seek.assert_called_once_with(0)


def test_a_read_write_route_with_a_replica_swaps_to_a_read_write_cursor():
    this, env = _make(readonly_route=False, replica=True)
    served = _run(this, env, lambda func, env, participant=None: func())

    assert served == "served"
    assert current_worker_thread().cursor_mode == "rw"
    assert this.first_cursor.closed
    assert len(this.calls["opened"]) == 1
    assert env.rebound_to is this.calls["opened"][0]


@pytest.mark.parametrize("finished", ["committed", "closed"])
def test_readonly_error_after_transaction_finished_is_never_replayed(finished):
    this, env = _make(readonly_route=True, replica=True)

    def retrying(func, env, participant=None):
        if finished == "committed":
            env.cr.commit_count += 1
        else:
            env.cr.close()
        raise psycopg.errors.ReadOnlySqlTransaction("postcommit write")

    with mock.patch.object(_serve, "RequestRetryParticipant") as participant:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            _run(this, env, retrying)
        participant.return_value.on_rollback.assert_not_called()
    assert this.calls["opened"] == []
    assert this.calls["reset_for_replay"] == []
    assert this.first_cursor.rollbacks == 0


def test_a_mode_the_router_recorded_is_kept_for_the_access_log():
    this, env = _make(readonly_route=True, replica=False)
    current_worker_thread().cursor_mode = "ro->rw"
    served = _run(this, env, lambda func, env, participant=None: func())

    assert served == "served"
    assert current_worker_thread().cursor_mode == "ro->rw", (
        "a request pinned to the primary must not read as a plain rw route"
    )


@pytest.mark.parametrize("stamped", ["ro", "ro->rw"])
def test_a_write_route_reads_rw_whatever_the_speculative_acquisition_stamped(stamped):
    this, env = _make(readonly_route=False, replica=True)
    current_worker_thread().cursor_mode = stamped
    served = _run(this, env, lambda func, env, participant=None: func())

    assert served == "served"
    assert current_worker_thread().cursor_mode == "rw", (
        "the registry stamps the read-only probe before the route's mode is "
        "known; a write route must not log as a replica read"
    )

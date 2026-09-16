import typing

import pytest

from odoo.db import settings as pool_settings
from odoo.db.replica import ReplicaRouter
from odoo.libs.worker_thread import current_worker_thread
from odoo.orm.runtime.registry import Registry


class _Cursor:
    def __init__(self, label):
        self.label = label

    def close(self):
        pass


class _Conn:
    def __init__(self, label):
        self.label = label

    def cursor(self):
        return _Cursor(self.label)


class _Router(ReplicaRouter):
    __slots__ = ("decisions",)

    def __init__(self, decisions):
        super().__init__(typing.cast("typing.Any", _Conn("primary")))
        self.decisions = list(decisions)

    def cursor(self, readonly=False, *, pin_key=None):
        cr, mode = self.decisions.pop(0)
        return typing.cast("typing.Any", cr), mode


def _make_registry(*decisions):
    reg = object.__new__(Registry)
    reg.db_name = "_breaker_db"
    reg._replica = _Router(decisions)
    return reg


def test_the_registry_hands_back_whatever_the_router_decided():
    reg = _make_registry(("replica-cursor", "ro"), ("primary-cursor", "rw"))
    assert reg.cursor(readonly=True) == "replica-cursor"
    assert reg.cursor() == "primary-cursor"


def test_a_replica_decision_is_recorded_on_the_request_thread():
    reg = _make_registry(("primary-cursor", "ro->rw"), ("replica-cursor", "ro"))
    thread = current_worker_thread()
    thread.cursor_mode = "unset"
    try:
        reg.cursor(readonly=True)
        assert thread.cursor_mode == "ro->rw"
        reg.cursor(readonly=True)
        assert thread.cursor_mode == "ro"
    finally:
        del thread.cursor_mode


def test_a_primary_decision_leaves_the_request_mode_alone():
    reg = _make_registry(("primary-cursor", "rw"), ("primary-cursor", "rw"))
    thread = current_worker_thread()
    thread.cursor_mode = "unset"
    try:
        reg.cursor()
        reg.cursor(readonly=True)
        assert thread.cursor_mode == "unset"
    finally:
        del thread.cursor_mode


def test_outside_a_request_no_mode_is_written():
    reg = _make_registry(("replica-cursor", "ro"))
    thread = current_worker_thread()
    assert not hasattr(thread, "cursor_mode")
    reg.cursor(readonly=True)
    assert not hasattr(thread, "cursor_mode")


def test_the_registry_holds_no_replica_state_of_its_own():
    reg = _make_registry()
    for gone in (
        "_db",
        "_db_readonly",
        "_db_readonly_failed_time",
        "_replica_breaker",
        "_replica_lag",
        "_sample_replica_lag",
    ):
        assert not hasattr(reg, gone), (
            f"{gone} is the ReplicaRouter's now; the registry keeps only the "
            f"thread's cursor mode"
        )


def test_the_real_router_is_what_init_builds(monkeypatch):
    import odoo.db
    from odoo.orm.runtime import registry as registry_module

    connections = []

    def fake_connect(db_name, readonly=False):
        connections.append((db_name, readonly))
        return _Conn("replica" if readonly else "primary")

    monkeypatch.setattr(odoo.db, "db_connect", fake_connect)
    monkeypatch.setattr(registry_module, "is_readonly_cursor_enabled", lambda: True)
    monkeypatch.setattr(Registry, "_probe_capabilities", lambda self, cr, name: None)

    reg = object.__new__(Registry)
    with pool_settings.override(replica_max_lag=12.0):
        reg.init("_router_db")

    assert isinstance(reg._replica, ReplicaRouter)
    assert connections == [("_router_db", False), ("_router_db", True)]
    assert reg._replica.lag.max_lag == 12.0
    assert reg._replica.readonly is not None


if __name__ == "__main__":
    pytest.main([__file__])

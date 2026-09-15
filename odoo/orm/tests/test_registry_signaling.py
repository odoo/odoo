import threading
import typing

import psycopg
import pytest

import odoo.db
from odoo.orm.runtime import registry as registry_module
from odoo.orm.runtime._registry_signaling import SIGNALING_TABLES, _RegistryCaches
from odoo.orm.runtime.registry import CACHES_BY_KEY, Registry
from odoo.tests import result as result_module


def _make_registry(db_name, registry_sequence, cache_sequence, *, ready=True):
    reg = object.__new__(Registry)
    reg.db_name = db_name
    reg.ready = ready
    reg.registry_sequence = registry_sequence
    reg.cache_sequences = dict.fromkeys(CACHES_BY_KEY, cache_sequence)
    reg._caches = _RegistryCaches()
    reg._invalidation_flags = threading.local()
    return reg


class _SeqCursor:
    def __init__(self, registry_sequence, cache_sequences):
        self._row = (
            registry_sequence,
            *(cache_sequences[name] for name in CACHES_BY_KEY),
        )
        self.plans_discarded = 0

    def execute(self, query, params=None, **kwargs):
        pass

    def fetchone(self):
        return self._row

    def invalidate_cached_plans(self):
        self.plans_discarded += 1


def _fail(what):
    def boom(*args, **kwargs):
        raise AssertionError(f"{what} must not be called")

    return boom


def _db_caches(value, **overrides):
    caches = dict.fromkeys(CACHES_BY_KEY, value)
    caches.update(overrides)
    return caches


def test_reload_when_db_registry_sequence_ahead(monkeypatch):
    reg = _make_registry("_sig_ahead_db", 5, 3)
    rebuilt = _make_registry("_sig_ahead_db", 6, 4)
    calls = []
    monkeypatch.setattr(
        odoo.db, "drain_db", lambda db_name: calls.append(("drain", db_name))
    )

    def fake_new(cls, db_name):
        calls.append(("new", db_name))
        return rebuilt

    monkeypatch.setattr(Registry, "new", classmethod(fake_new))

    cur = _SeqCursor(6, _db_caches(3))
    result = reg.check_signaling(cur)

    assert result is rebuilt
    assert calls == [("drain", "_sig_ahead_db"), ("new", "_sig_ahead_db")]
    assert cur.plans_discarded == 1


def test_no_reload_when_db_registry_sequence_behind(monkeypatch):
    reg = _make_registry("_sig_lag_db", 7, 5)
    reg._caches.lrus["default"]["k"] = "v"
    monkeypatch.setattr(odoo.db, "drain_db", _fail("drain_db"))
    monkeypatch.setattr(Registry, "new", classmethod(_fail("Registry.new")))

    cur = _SeqCursor(5, _db_caches(4))
    result = reg.check_signaling(cur)

    assert result is reg
    assert reg.registry_sequence == 7
    assert reg.cache_sequences == dict.fromkeys(CACHES_BY_KEY, 5)
    assert reg._caches.lrus["default"]["k"] == "v"
    assert cur.plans_discarded == 0


def test_adopt_registry_published_by_other_thread(monkeypatch):
    name = "_sig_adopt_db"
    stale = _make_registry(name, 5, 3)
    published = _make_registry(name, 6, 4)
    Registry.registries[name] = published
    try:
        monkeypatch.setattr(odoo.db, "drain_db", _fail("drain_db"))
        monkeypatch.setattr(Registry, "new", classmethod(_fail("Registry.new")))

        cur = _SeqCursor(6, _db_caches(4))
        result = stale.check_signaling(cur)

        assert result is published
        assert cur.plans_discarded == 1
    finally:
        Registry.registries.pop(name, None)


def test_no_adopt_when_published_registry_too_old(monkeypatch):
    name = "_sig_noadopt_db"
    stale = _make_registry(name, 5, 3)
    published = _make_registry(name, 5, 3)
    Registry.registries[name] = published
    rebuilt = _make_registry(name, 6, 4)
    calls = []
    try:
        monkeypatch.setattr(odoo.db, "drain_db", lambda db_name: None)

        def fake_new(cls, db_name):
            calls.append(db_name)
            return rebuilt

        monkeypatch.setattr(Registry, "new", classmethod(fake_new))

        cur = _SeqCursor(6, _db_caches(4))
        result = stale.check_signaling(cur)

        assert result is rebuilt
        assert calls == [name]
        assert cur.plans_discarded == 1
    finally:
        Registry.registries.pop(name, None)


def test_cache_cleared_when_db_cache_sequence_ahead():
    reg = _make_registry("_sig_cache_db", 5, 3)
    reg._caches.lrus["assets"]["a"] = 1
    reg._caches.lrus["templates.cached_values"]["t"] = 1
    reg._caches.lrus["default"]["d"] = 1

    result = reg.check_signaling(_SeqCursor(5, _db_caches(3, assets=4)))

    assert result is reg
    assert reg.cache_sequences["assets"] == 4
    assert "a" not in reg._caches.lrus["assets"]
    assert "t" not in reg._caches.lrus["templates.cached_values"]
    assert reg._caches.lrus["default"]["d"] == 1
    assert reg.cache_sequences["default"] == 3


def test_cache_kept_when_db_cache_sequence_behind():
    reg = _make_registry("_sig_cache_lag_db", 5, 6)
    reg._caches.lrus["assets"]["a"] = 1

    result = reg.check_signaling(_SeqCursor(5, _db_caches(4)))

    assert result is reg
    assert reg.cache_sequences == dict.fromkeys(CACHES_BY_KEY, 6)
    assert reg._caches.lrus["assets"]["a"] == 1


def test_adopted_registry_with_lagging_cache_sequences_is_invalidated(monkeypatch):
    name = "_sig_adopt_stale_cache_db"
    stale = _make_registry(name, 5, 3)
    published = _make_registry(name, 6, 4)
    published._caches.lrus["assets"]["stale_key"] = "stale_value"
    Registry.registries[name] = published
    try:
        monkeypatch.setattr(odoo.db, "drain_db", _fail("drain_db"))
        monkeypatch.setattr(Registry, "new", classmethod(_fail("Registry.new")))

        cur = _SeqCursor(6, _db_caches(5))
        result = stale.check_signaling(cur)

        assert result is published
        assert "stale_key" not in published._caches.lrus["assets"]
        assert published.cache_sequences == dict.fromkeys(CACHES_BY_KEY, 5)
        assert cur.plans_discarded == 1
    finally:
        Registry.registries.pop(name, None)


def test_cache_check_is_noop_on_freshly_rebuilt_registry(monkeypatch):
    reg = _make_registry("_sig_rebuild_fresh_db", 5, 3)
    rebuilt = _make_registry("_sig_rebuild_fresh_db", 6, 4)
    rebuilt._caches.lrus["assets"]["fresh"] = 1
    monkeypatch.setattr(odoo.db, "drain_db", lambda db_name: None)
    monkeypatch.setattr(Registry, "new", classmethod(lambda cls, db_name: rebuilt))

    result = reg.check_signaling(_SeqCursor(6, _db_caches(4)))

    assert result is rebuilt
    assert rebuilt._caches.lrus["assets"]["fresh"] == 1
    assert rebuilt.cache_sequences == dict.fromkeys(CACHES_BY_KEY, 4)


class _DyingCursor:
    def execute(self, query, params=None, **kwargs):
        raise psycopg.OperationalError("server closed the connection unexpectedly")

    def close(self):
        pass


def test_dead_db_mid_query_on_own_cursor_deletes_registry(monkeypatch):
    name = "_sig_dead_mid_query_db"
    reg = _make_registry(name, 5, 3)
    Registry.registries[name] = reg
    monkeypatch.setattr(Registry, "cursor", lambda self, readonly=False: _DyingCursor())
    deleted = []
    monkeypatch.setattr(
        Registry, "remove", classmethod(lambda cls, db_name: deleted.append(db_name))
    )
    try:
        with pytest.raises(psycopg.OperationalError):
            reg.check_signaling()
        assert deleted == [name]
    finally:
        Registry.registries.pop(name, None)


def test_dead_db_at_open_deletes_registry(monkeypatch):
    name = "_sig_dead_at_open_db"
    reg = _make_registry(name, 5, 3)
    Registry.registries[name] = reg

    def dying_open(self, readonly=False):
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(Registry, "cursor", dying_open)
    deleted = []
    monkeypatch.setattr(
        Registry, "remove", classmethod(lambda cls, db_name: deleted.append(db_name))
    )
    try:
        with pytest.raises(psycopg.OperationalError):
            reg.check_signaling()
        assert deleted == [name]
    finally:
        Registry.registries.pop(name, None)


def test_dead_caller_cursor_keeps_registry(monkeypatch):
    name = "_sig_dead_caller_cr_db"
    reg = _make_registry(name, 5, 3)
    Registry.registries[name] = reg
    monkeypatch.setattr(Registry, "remove", classmethod(_fail("Registry.relete")))
    try:
        with pytest.raises(psycopg.OperationalError):
            reg.check_signaling(_DyingCursor())
    finally:
        Registry.registries.pop(name, None)


def test_get_sequences_rejects_row_length_drift():

    class _ShortRowCursor:
        def execute(self, query, params=None, **kwargs):
            pass

        def fetchone(self):
            return (1, *([1] * (len(CACHES_BY_KEY) - 1)))

    reg = _make_registry("_seq_strict_db", 1, 1)
    with pytest.raises(ValueError):
        reg.get_sequences(_ShortRowCursor())


def test_signal_changes_records_the_id_the_database_generated(monkeypatch):

    class _ReturningCursor:
        def __init__(self):
            self.queries = []
            self._next = 40

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params=None, **kwargs):
            self.queries.append(query.code if hasattr(query, "code") else str(query))

        def fetchone(self):
            value = self._next
            self._next += 1
            return (value,)

    cur = _ReturningCursor()
    reg = _make_registry("_signal_returning_db", 1, 1)
    monkeypatch.setattr(Registry, "cursor", lambda self, readonly=False: cur)
    reg.registry_invalidated = True
    reg.cache_invalidated.add("default")

    reg.signal_changes()

    assert all("RETURNING id" in q for q in cur.queries), (
        f"signal_changes stopped asking the database for the id it generated: "
        f"{cur.queries}"
    )
    assert reg.registry_sequence == 40
    assert reg.cache_sequences["default"] == 41


def test_signalled_id_falls_back_when_no_row_comes_back():

    class _NoRowCursor:
        def fetchone(self):
            return None

    assert Registry._get_signalled_id(typing.cast("typing.Any", _NoRowCursor()), 7) == 8


def test_get_sequences_reads_every_serial_once_and_coalesces_an_unused_one():

    class _SequenceCursor:
        def __init__(self):
            self.sql = ""
            self.params = ()

        def execute(self, query, params=None, **kwargs):
            self.sql = query.code if hasattr(query, "code") else str(query)
            self.params = query.params if hasattr(query, "params") else params

        def fetchone(self):
            return (0, *([0] * len(CACHES_BY_KEY)))

    cur = _SequenceCursor()
    reg = _make_registry("_seq_empty_db", -1, -1)
    registry_sequence, cache_sequences = reg.get_sequences(cur)

    assert cur.sql.count("coalesce(pg_sequence_last_value(") == len(SIGNALING_TABLES), (
        "one sequence read per watermark, guarded against a never-used serial"
    )
    assert "max(id)" not in cur.sql, "a max(id) subselect plans per call"
    assert tuple(cur.params) == tuple(f"{table}_id_seq" for table in SIGNALING_TABLES)
    assert registry_sequence == 0
    assert cache_sequences == dict.fromkeys(CACHES_BY_KEY, 0)

    assert (registry_sequence > reg.registry_sequence) is True


class _SetupCursor:
    def __init__(self):
        self.queries = []
        self._row = (1, *([1] * len(CACHES_BY_KEY)))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None, **kwargs):
        self.queries.append(query.code if hasattr(query, "code") else str(query))

    def fetchone(self):
        return self._row


def _run_setup_signaling(monkeypatch, existing_tables):
    reg = _make_registry("_sig_setup_db", -1, -1)
    cur = _SetupCursor()
    monkeypatch.setattr(Registry, "cursor", lambda self, readonly=False: cur)
    monkeypatch.setattr(
        registry_module.sql, "get_tables_existing", lambda cr, names: existing_tables
    )
    reg.setup_signaling()
    return reg, cur


def test_setup_signaling_creates_tables_if_not_exists(monkeypatch):
    reg, cur = _run_setup_signaling(monkeypatch, existing_tables=())

    creates = [q for q in cur.queries if q.startswith("CREATE")]
    inserts = [q for q in cur.queries if q.startswith("INSERT")]
    assert len(creates) == len(SIGNALING_TABLES)
    assert all(q.startswith("CREATE TABLE IF NOT EXISTS") for q in creates)
    assert len(inserts) == len(SIGNALING_TABLES)
    assert reg.registry_sequence == 1
    assert reg.cache_sequences == dict.fromkeys(CACHES_BY_KEY, 1)


def test_setup_signaling_does_not_reseed_existing_tables(monkeypatch):
    reg, cur = _run_setup_signaling(
        monkeypatch, existing_tables=tuple(SIGNALING_TABLES)
    )

    assert not [q for q in cur.queries if q.startswith(("CREATE", "INSERT"))]
    assert reg.registry_sequence == 1


def test_setup_signaling_seeds_only_missing_tables(monkeypatch):
    missing = SIGNALING_TABLES[0]
    _reg, cur = _run_setup_signaling(
        monkeypatch, existing_tables=tuple(SIGNALING_TABLES[1:])
    )

    creates = [q for q in cur.queries if q.startswith("CREATE")]
    inserts = [q for q in cur.queries if q.startswith("INSERT")]
    assert len(creates) == 1
    assert len(inserts) == 1
    assert missing in creates[0] and missing in inserts[0]


def test_clear_cache_unknown_name_raises_listing_valid_names():
    reg = _make_registry("_cc_db", 1, 1)
    reg._caches.lrus["assets"]["a"] = 1

    with pytest.raises(ValueError) as excinfo:
        reg.clear_cache("assets", "bogus")

    message = str(excinfo.value)
    assert "bogus" in message
    for known in CACHES_BY_KEY:
        assert known in message
    assert reg._caches.lrus["assets"]["a"] == 1
    assert not reg.cache_invalidated


def test_clear_cache_rejects_dotted_subcache_name():
    reg = _make_registry("_cc_dotted_db", 1, 1)
    with pytest.raises(ValueError, match=r"templates\.cached_values"):
        reg.clear_cache("templates.cached_values")


def test_clear_cache_known_name_still_works():
    reg = _make_registry("_cc_ok_db", 1, 1)
    reg._caches.lrus["assets"]["a"] = 1

    reg.clear_cache("assets")

    assert "a" not in reg._caches.lrus["assets"]
    assert reg.cache_invalidated == {"assets"}


def test_new_failure_cleanup_survives_nested_delete(monkeypatch):
    name = "_new_cleanup_db"

    def fake_init(self, db_name):
        self.db_name = db_name

    def fake_setup_signaling(self):
        Registry.registries.pop(self.db_name, None)
        raise RuntimeError("boom")

    monkeypatch.setattr(Registry, "init", fake_init)
    monkeypatch.setattr(Registry, "setup_signaling", fake_setup_signaling)
    try:
        with pytest.raises(RuntimeError, match="boom"):
            Registry.new(name)
    finally:
        Registry.registries.pop(name, None)
    assert name not in Registry.registries


class _ExplodingLock:
    def __enter__(self):
        raise AssertionError("class lock must not be taken on the fast path")

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_registry_lookup_of_ready_registry_is_lock_free(monkeypatch):
    name = "_fastpath_db"
    ready_reg = _make_registry(name, 1, 1)
    Registry.registries[name] = ready_reg
    try:
        monkeypatch.setattr(Registry, "_lock", _ExplodingLock())
        assert Registry(name) is ready_reg
    finally:
        Registry.registries.pop(name, None)


def test_registry_lookup_of_inflight_registry_takes_the_lock(monkeypatch):
    name = "_fastpath_notready_db"
    building = _make_registry(name, 1, 1, ready=False)
    Registry.registries[name] = building
    real_lock = threading.RLock()
    acquired = []

    class _RecordingLock:
        def __enter__(self):
            acquired.append(True)
            return real_lock.__enter__()

        def __exit__(self, exc_type, exc_value, traceback):
            return real_lock.__exit__(exc_type, exc_value, traceback)

    monkeypatch.setattr(Registry, "_lock", _RecordingLock())
    try:
        assert Registry(name) is building
        assert acquired, "not-ready registry must be resolved under the lock"
    finally:
        Registry.registries.pop(name, None)


def test_registry_empty_db_name_rejected():
    with pytest.raises(ValueError, match="Missing database name"):
        Registry("")


def test_assertion_report_is_none_outside_test_mode(monkeypatch):
    monkeypatch.setitem(registry_module.config.options, "test_enable", False)
    assert result_module.assertion_report("some_db") is None


def test_assertion_report_survives_a_registry_reload(monkeypatch):
    monkeypatch.setitem(registry_module.config.options, "test_enable", True)
    monkeypatch.setattr(result_module, "_ASSERTION_REPORTS", {})

    first = result_module.assertion_report("db_a")
    assert first is not None
    assert result_module.assertion_report("db_a") is first


def test_assertion_report_is_per_database(monkeypatch):
    monkeypatch.setitem(registry_module.config.options, "test_enable", True)
    monkeypatch.setattr(result_module, "_ASSERTION_REPORTS", {})

    assert result_module.assertion_report("db_a") is not result_module.assertion_report(
        "db_b"
    )


def test_recorded_failure_is_still_visible_after_a_reload(monkeypatch):
    monkeypatch.setitem(registry_module.config.options, "test_enable", True)
    monkeypatch.setattr(result_module, "_ASSERTION_REPORTS", {})

    report = result_module.assertion_report("db_a")
    assert report is not None
    report.failures_count += 1
    assert not report.wasSuccessful()
    reloaded = result_module.assertion_report("db_a")
    assert reloaded is not None
    assert not reloaded.wasSuccessful()

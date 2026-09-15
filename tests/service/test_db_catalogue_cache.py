from unittest.mock import patch

import pytest

from odoo.service.db import listing


@pytest.fixture(autouse=True)
def fresh():
    listing._invalidate_catalog_cache()
    yield
    listing._invalidate_catalog_cache()


@pytest.fixture
def cfg():
    return {"list_db": True, "dbfilter": ".*", "db_name": [], "db_template": "tpl"}


class TestTheCatalogueScanIsShared:
    def test_repeated_calls_hit_postgres_once(self, cfg):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", return_value=["a", "b"]
            ) as q,
        ):
            for _ in range(10):
                assert listing.list_dbs(True) == ["a", "b"]
        assert q.call_count == 1, (
            "the pg_database scan costs ~4.7ms and sits on the db_exist RPC "
            "every client makes on connect"
        )

    def test_the_caller_cannot_poison_the_cache(self, cfg):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", return_value=["a"]),
        ):
            first = listing.list_dbs(True)
            first.append("injected")
            assert listing.list_dbs(True) == ["a"]

    def test_a_catalogue_change_by_this_process_is_seen_at_once(self, cfg):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", side_effect=[["a"], ["a", "b"]]
            ),
        ):
            assert listing.list_dbs(True) == ["a"]
            listing.invalidate_catalog_caches()
            assert listing.list_dbs(True) == ["a", "b"]

    def test_the_cache_is_dropped_before_the_listeners_run(self, cfg):
        seen = []

        def listener():
            seen.append(listing._catalog_cache)

        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_catalog_listeners", [listener]),
            patch.object(listing, "_get_catalog_uncached", return_value=["a"]),
        ):
            listing.list_dbs(True)
            listing.invalidate_catalog_caches()
        assert seen == [None], (
            "a listener that re-reads the catalogue would repopulate it with "
            "the rows the invalidation exists to discard"
        )

    def test_the_ttl_expires(self, cfg, monkeypatch):
        clock = [1000.0]
        monkeypatch.setattr(listing.time, "monotonic", lambda: clock[0])
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", side_effect=[["a"], ["b"]]
            ) as q,
        ):
            assert listing.list_dbs(True) == ["a"]
            clock[0] += listing.CATALOG_CACHE_TTL_S + 0.01
            assert listing.list_dbs(True) == ["b"]
        assert q.call_count == 2

    def test_a_zero_ttl_disables_it(self, cfg, monkeypatch):
        monkeypatch.setenv("ODOO_DB_CATALOGUE_CACHE_TTL", "0")
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", return_value=["a"]) as q,
        ):
            listing.list_dbs(True)
            listing.list_dbs(True)
        assert q.call_count == 2

    def test_the_configured_list_shortcut_never_touches_postgres(self):
        cfg = {"list_db": True, "dbfilter": "", "db_name": ["b", "a"]}
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached") as q,
        ):
            assert listing.list_dbs(True) == ["a", "b"]
        q.assert_not_called()

    def test_a_failed_scan_is_not_cached(self, cfg):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", side_effect=[None, ["a"]]
            ) as q,
        ):
            assert listing.list_dbs(True) == [], (
                "the database selector renders at auth=none; a scan failure "
                "must answer empty rather than raise"
            )
            assert listing.list_dbs(True) == ["a"], (
                "one transient PostgreSQL hiccup blanked the database list for "
                "the whole TTL"
            )
        assert q.call_count == 2

    def test_list_db_false_is_still_refused_without_force(self, cfg):
        cfg["list_db"] = False
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", return_value=["a"]),
            pytest.raises(listing.odoo.exceptions.AccessDenied),
        ):
            listing.list_dbs()


class TestAnInvalidationCannotBeOutrunByAQueryInFlight:
    """`_get_catalog_uncached` runs outside the lock, so a create/drop can land mid-scan.

    The scan is ~4.7ms of round trip during which `_create_empty_database`,
    `drop_database`, `rename_database` and `duplicate_database` all call
    `invalidate_catalog_caches`.  Storing the scan's result unconditionally
    undoes that invalidation and serves the pre-change list for a full TTL --
    long enough for `check_db_exposed` to refuse a dump of a database that was
    just created, and to admit one that was just dropped.
    """

    def test_a_creation_during_the_scan_is_not_undone_by_it(self, cfg):
        stale = ["alpha"]

        def slow_scan():
            answer = list(stale)  # PostgreSQL answered here, pre-create
            listing.invalidate_catalog_caches()  # ...and the create lands now
            return answer

        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", side_effect=slow_scan) as q,
        ):
            assert listing.list_dbs(True) == ["alpha"]
            stale = ["alpha", "beta"]
            assert listing.list_dbs(True) == ["alpha", "beta"], (
                "the outrun scan cached its pre-create list, so the new "
                "database stayed invisible for the whole TTL"
            )
        assert q.call_count == 2

    def test_an_unoutrun_scan_still_caches(self, cfg):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", return_value=["a"]) as q,
        ):
            assert listing.list_dbs(True) == ["a"]
            assert listing.list_dbs(True) == ["a"]
        assert q.call_count == 1, "the generation guard disabled the cache"


class TestAnExpiryDoesNotStampedePostgres:
    def test_concurrent_cold_callers_share_one_scan(self, cfg):
        import threading

        started = threading.Event()
        release = threading.Event()
        calls = []

        def scan():
            calls.append(1)
            started.set()
            release.wait(5)
            return ["a"]

        results = []
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", side_effect=scan),
        ):
            threads = [
                threading.Thread(target=lambda: results.append(listing.list_dbs(True)))
                for _ in range(8)
            ]
            for thread in threads:
                thread.start()
            assert started.wait(5)
            release.set()
            for thread in threads:
                thread.join(5)
        assert results == [["a"]] * 8
        assert len(calls) == 1, (
            "each scan borrows a maintenance connection on top of the caller's "
            "request cursor; eight at once exhausted db_maxconn"
        )

    def test_a_caller_during_a_refresh_gets_the_previous_list(self, cfg, monkeypatch):
        import threading

        clock = [1000.0]
        monkeypatch.setattr(listing.time, "monotonic", lambda: clock[0])
        started = threading.Event()
        release = threading.Event()

        def slow_scan():
            started.set()
            release.wait(5)
            return ["b"]

        with patch.object(listing.odoo.tools, "config", cfg):
            with patch.object(listing, "_get_catalog_uncached", return_value=["a"]):
                assert listing.list_dbs(True) == ["a"]
            clock[0] += listing.CATALOG_CACHE_TTL_S + 0.01
            with patch.object(
                listing, "_get_catalog_uncached", side_effect=slow_scan
            ) as q:
                refresher = threading.Thread(target=lambda: listing.list_dbs(True))
                refresher.start()
                assert started.wait(5)
                assert listing.list_dbs(True) == ["a"]
                release.set()
                refresher.join(5)
                assert q.call_count == 1
            assert listing.list_dbs(True) == ["b"]

    def test_an_invalidated_list_is_never_served_as_stale(self, cfg, monkeypatch):
        import threading

        clock = [1000.0]
        monkeypatch.setattr(listing.time, "monotonic", lambda: clock[0])
        started = threading.Event()
        release = threading.Event()
        answers = iter([["a"], ["b"], ["c"]])

        def scan():
            value = next(answers)
            if value == ["b"]:
                started.set()
                release.wait(5)
            return value

        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached", side_effect=scan),
        ):
            assert listing.list_dbs(True) == ["a"]
            clock[0] += listing.CATALOG_CACHE_TTL_S + 0.01
            refresher = threading.Thread(target=lambda: listing.list_dbs(True))
            refresher.start()
            assert started.wait(5)
            listing.invalidate_catalog_caches()
            seen = []
            waiter = threading.Thread(
                target=lambda: seen.append(listing.list_dbs(True))
            )
            waiter.start()
            waiter.join(0.2)
            assert waiter.is_alive(), "served the invalidated list instead of waiting"
            release.set()
            refresher.join(5)
            waiter.join(5)
        assert seen == [["c"]], (
            "the scan outrun by the invalidation must not be cached; the waiter rescans"
        )


class _FakeCursor:
    def __init__(self, row=None, error=None, closed=False):
        self.row = row
        self.error = error
        self.closed = closed
        self.savepoints = 0
        self.statements = []

    def savepoint(self, flush=True):
        import contextlib

        self.savepoints += 1
        return contextlib.nullcontext()

    def execute(self, query, params=None):
        self.statements.append(query)
        if self.error is not None:
            raise self.error

    def fetchone(self):
        return self.row


class TestTheScanUsesTheCallersConnection:
    def test_a_primary_cursor_answers_without_borrowing(self, cfg):
        cr = _FakeCursor(row=(False, ["a", "b"]))
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached") as borrow,
        ):
            assert listing.list_dbs(True, cr=cr) == ["a", "b"]
            assert listing.list_dbs(True) == ["a", "b"], "the answer is cached"
        borrow.assert_not_called()
        assert cr.savepoints == 1, (
            "a failing scan must not abort the caller's transaction"
        )

    def test_a_standby_is_not_trusted(self, cfg):
        cr = _FakeCursor(row=(True, ["stale"]))
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", return_value=["fresh"]
            ) as borrow,
        ):
            assert listing.list_dbs(True, cr=cr) == ["fresh"]
        borrow.assert_called_once_with()

    @pytest.mark.parametrize(
        "cr",
        [
            _FakeCursor(error=RuntimeError("in a pipeline")),
            _FakeCursor(closed=True),
            None,
        ],
        ids=["failing", "closed", "absent"],
    )
    def test_no_usable_cursor_falls_back_to_the_maintenance_scan(self, cfg, cr):
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(
                listing, "_get_catalog_uncached", return_value=["m"]
            ) as borrow,
        ):
            assert listing.list_dbs(True, cr=cr) == ["m"]
        borrow.assert_called_once_with()

    def test_a_zero_ttl_still_prefers_the_callers_cursor(self, cfg, monkeypatch):
        monkeypatch.setenv("ODOO_DB_CATALOGUE_CACHE_TTL", "0")
        cr = _FakeCursor(row=(False, ["a"]))
        with (
            patch.object(listing.odoo.tools, "config", cfg),
            patch.object(listing, "_get_catalog_uncached") as borrow,
        ):
            assert listing.list_dbs(True, cr=cr) == ["a"]
        borrow.assert_not_called()


def test_get_dbs_served_hands_the_request_cursor_down(monkeypatch):
    from types import SimpleNamespace

    from odoo.http import _dbfilter

    cr = object()
    monkeypatch.setattr(
        _dbfilter, "request", SimpleNamespace(env=SimpleNamespace(cr=cr))
    )
    with (
        patch.object(
            _dbfilter.odoo.service.db, "list_dbs", return_value=["a"]
        ) as list_dbs,
        patch.object(_dbfilter, "filter_dbs_served", side_effect=lambda dbs, host: dbs),
    ):
        assert _dbfilter.get_dbs_served(True) == ["a"]
    list_dbs.assert_called_once_with(True, cr=cr)

from unittest.mock import MagicMock, patch

import psycopg
import pytest

import odoo
from odoo.service.db import listing


@pytest.fixture(autouse=True)
def _fresh_catalogue():
    """The catalogue cache is process-global; no test may inherit another's."""
    listing._invalidate_catalog_cache()
    yield
    listing._invalidate_catalog_cache()


@pytest.fixture
def cfg():
    values = {
        "list_db": True,
        "dbfilter": "",
        "db_name": "",
        "db_template": "template0",
    }
    with patch.object(odoo.tools, "config", values):
        yield values


class TestCatalogListeners:
    @pytest.fixture(autouse=True)
    def _isolate(self):
        original = list(listing._catalog_listeners)
        listing._catalog_listeners.clear()
        yield
        listing._catalog_listeners[:] = original

    def test_a_raising_listener_does_not_stop_the_next_one(self):
        ran = []
        listing.register_catalog_listener(lambda: ran.append("first"))
        listing.register_catalog_listener(
            MagicMock(side_effect=RuntimeError("cache backend down"))
        )
        listing.register_catalog_listener(lambda: ran.append("third"))

        listing.invalidate_catalog_caches()

        assert ran == ["first", "third"], (
            "a listener that raised swallowed the ones registered after it; "
            "their caches stay stale until their TTL expires"
        )

    def test_a_raising_listener_does_not_reach_the_caller(self):
        listing.register_catalog_listener(MagicMock(side_effect=RuntimeError("boom")))
        listing.invalidate_catalog_caches()

    def test_with_no_listeners_it_is_a_no_op(self):
        listing.invalidate_catalog_caches()


class TestExpDbExist:
    def _connect(self, exc=None):
        db = MagicMock()
        if exc is not None:
            db.cursor.side_effect = exc
        return patch.object(odoo.db, "db_connect", return_value=db)

    def test_a_connectable_database_exists(self):
        with self._connect():
            assert listing.exp_db_exist("live") is True

    def test_a_missing_database_is_false(self):
        with self._connect(psycopg.errors.InvalidCatalogName()):
            assert listing.exp_db_exist("gone") is False

    def test_a_transient_failure_is_ALSO_false(self):
        with self._connect(psycopg.OperationalError("pool saturated")):
            assert listing.exp_db_exist("live") is False, (
                "the two must be indistinguishable to the caller: this is "
                "reachable at auth=none, so a distinguishable answer turns "
                "pool pressure into a database-existence oracle"
            )

    def test_even_an_unexpected_exception_is_false_and_not_raised(self):
        with self._connect(ValueError("something else entirely")):
            assert listing.exp_db_exist("live") is False


class TestListDbsGate:
    def test_listing_is_denied_when_list_db_is_off(self, cfg):
        cfg["list_db"] = False
        with pytest.raises(odoo.exceptions.AccessDenied):
            listing.list_dbs()

    def test_force_is_what_the_server_itself_uses_to_bypass_the_gate(self, cfg):
        cfg["list_db"] = False
        cfg["db_name"] = ["only_this"]
        assert listing.list_dbs(force=True) == ["only_this"], (
            "force must skip the AccessDenied; it is how internal callers list "
            "databases on an instance that does not expose the list over RPC"
        )

    def test_a_configured_db_name_short_circuits_before_any_sql(self, cfg):
        cfg["db_name"] = ["beta", "alpha"]
        with patch.object(odoo.db, "db_connect") as connect:
            assert listing.list_dbs() == ["alpha", "beta"], "sorted"
        connect.assert_not_called()

    def test_the_shortcut_is_safe_only_because_db_name_is_a_list(self):
        from odoo.tools import config

        option = config.options_index["db_name"]
        assert option.type == "comma", (
            f"db_name now parses as {option.type!r}; if that is no longer a "
            f"list, sorted() in list_dbs silently returns its characters"
        )
        assert option.my_default == [], option.my_default

    def test_a_dbfilter_sends_it_back_to_the_sql_branch(self, cfg):
        cfg["db_name"] = ["only_this"]
        cfg["dbfilter"] = ".*"
        with patch.object(odoo.db, "db_connect") as connect:
            connect.return_value.cursor.return_value.fetchone.return_value = (
                False,
                ["x"],
            )
            assert listing.list_dbs() == ["x"], (
                "with a dbfilter the configured db_name is a default, not the "
                "whole answer, so the catalogue has to be read"
            )


class TestListDbsSqlFailure:
    def test_a_failed_query_lists_nothing_rather_than_raising(self, cfg):
        db = MagicMock()
        db.cursor.return_value.execute.side_effect = psycopg.OperationalError("down")
        with patch.object(odoo.db, "db_connect", return_value=db):
            assert listing.list_dbs() == [], (
                "this renders the database selector at auth=none; an exception "
                "there is a stack trace to an anonymous caller"
            )


class TestListDbIncompatible:
    def _probe(self, *, table=True, version=None, pooled=(), raises=None):
        cr = MagicMock()
        cr.fetchone.return_value = (version,) if version is not None else None
        db = MagicMock()
        db.cursor.side_effect = raises
        if raises is None:
            db.cursor.return_value = cr
        closed = []
        return (
            patch.object(odoo.db, "db_connect", return_value=db),
            patch.object(odoo.db, "is_pooled", side_effect=lambda n: n in pooled),
            patch.object(odoo.db, "close_db", side_effect=closed.append),
            patch.object(listing._db_schema, "table_exists", return_value=table),
            closed,
        )

    def _run(self, databases, **kwargs):
        connect, pooled, close, table, closed = self._probe(**kwargs)
        with connect, pooled, close, table:
            return listing.list_db_incompatible(list(databases)), closed

    def test_a_matching_base_version_is_compatible(self):
        version = ".".join(str(v) for v in odoo.release.version_info[:2])
        result, _ = self._run(["ok"], version=f"{version}.1.0")
        assert result == []

    def test_a_different_base_version_is_incompatible(self):
        result, _ = self._run(["old"], version="1.0.1.0")
        assert result == ["old"]

    def test_a_database_with_no_ir_module_module_is_incompatible(self):
        result, _ = self._run(["blank"], table=False)
        assert result == ["blank"]

    def test_a_null_db_version_is_incompatible(self):
        result, _ = self._run(["halfbuilt"], version=None)
        assert result == ["halfbuilt"]

    def test_an_empty_db_version_is_incompatible(self):
        result, _ = self._run(["halfbuilt"], version="")
        assert result == ["halfbuilt"]

    def test_a_database_that_cannot_be_probed_is_incompatible(self):
        result, _ = self._run(["unreachable"], raises=psycopg.OperationalError("no"))
        assert result == ["unreachable"], (
            "it must fail CLOSED: offering an unreachable database as servable "
            "sends the next request into an error instead of a selector"
        )


class TestListDbIncompatibleLeavesPoolsAsItFoundThem:
    def _run(self, databases, **kwargs):
        return TestListDbIncompatible()._run(databases, **kwargs)

    def test_a_compatible_database_that_was_already_pooled_keeps_its_pool(self):
        version = ".".join(str(v) for v in odoo.release.version_info[:2])
        result, closed = self._run(["warm"], version=f"{version}.1.0", pooled=["warm"])
        assert result == []
        assert closed == [], (
            "closing a pool this call did not open costs the next request to "
            "that database a full rebuild, on every selector render"
        )

    def test_a_compatible_database_this_call_pooled_is_closed_again(self):
        version = ".".join(str(v) for v in odoo.release.version_info[:2])
        result, closed = self._run(["cold"], version=f"{version}.1.0", pooled=[])
        assert result == []
        assert closed == ["cold"], (
            "probing a database nobody was serving and leaving the pool behind "
            "is a leak — one per unserved database, per render"
        )

    def test_an_incompatible_database_is_closed_even_if_it_was_pooled(self):
        result, closed = self._run(["stale"], version="1.0.1.0", pooled=["stale"])
        assert result == ["stale"]
        assert closed == ["stale"], (
            "it will not be served, so the pool is not worth keeping warm"
        )


class TestListCountries:
    def test_it_reads_the_bundled_xml_with_no_database(self):
        countries = listing.exp_list_countries()
        assert len(countries) > 200
        assert all(len(code) == 2 for code, _ in countries)
        assert ["mx", "Mexico"] in countries, "the XML spells codes lowercase"

    def test_each_call_returns_a_fresh_mutable_list(self):
        first = listing.exp_list_countries()
        first.append(["ZZ", "Mutated"])
        assert ["ZZ", "Mutated"] not in listing.exp_list_countries(), (
            "the parse is memoized; handing out the cached object would let one "
            "caller's mutation reach every later one"
        )

    def test_the_parse_itself_happens_once(self):
        listing.exp_list_countries()
        before = listing._read_countries.cache_info().misses
        listing.exp_list_countries()
        assert listing._read_countries.cache_info().misses == before


class TestDbExistDoesNotPayForWhatTheListingProved:
    def _config(self, **overrides):
        base = {"list_db": True, "dbfilter": "", "db_name": []}
        return patch.dict(odoo.tools.config.options, {**base, **overrides})

    def test_the_catalogue_branch_answers_without_connecting(self):
        with (
            self._config(),
            patch.object(listing, "_get_catalog_cached", return_value=["alpha"]),
            patch.object(listing, "exp_db_exist") as connect,
        ):
            assert listing._rpc_db_exist("alpha") is True

        assert not connect.called, (
            "the catalogue query filters on datallowconn and datdba = "
            "current_user, so a name it returned demonstrably exists; opening a "
            "connection re-establishes what the listing already proved"
        )

    def test_the_db_name_branch_still_connects(self):
        """`db_name` states intent. It is not evidence the database was created."""
        with (
            self._config(db_name=["configured"]),
            patch.object(listing, "exp_db_exist", return_value=False) as connect,
        ):
            assert listing._rpc_db_exist("configured") is False

        connect.assert_called_once_with("configured")

    def test_a_configured_but_uncreated_database_is_not_reported_as_existing(self):
        with (
            self._config(db_name=["never_created"]),
            patch.object(listing, "exp_db_exist", return_value=False),
        ):
            assert listing._rpc_db_exist("never_created") is False, (
                "skipping the connection on this branch would answer True for "
                "every name an operator listed, created or not"
            )

    def test_a_name_absent_from_the_listing_never_connects(self):
        with (
            self._config(),
            patch.object(listing, "_get_catalog_cached", return_value=["alpha"]),
            patch.object(listing, "exp_db_exist") as connect,
        ):
            assert listing._rpc_db_exist("absent") is False
        assert not connect.called

    def test_the_branch_is_decided_in_one_place(self):
        """Both `list_dbs` and `_rpc_db_exist` ask the same predicate.

        Re-deriving "which source answered" at each call site is how the two
        drift; `_rpc_db_exist` is the caller that has to know.
        """
        with self._config(db_name=["configured"]):
            assert listing._is_db_list_configured() is True
            assert listing.list_dbs(True) == ["configured"]
        with self._config():
            assert listing._is_db_list_configured() is False
        with self._config(db_name=["configured"], dbfilter="^x"):
            assert listing._is_db_list_configured() is False, (
                "a dbfilter sends list_dbs to the catalogue even with db_name set"
            )

    def test_list_dbs_remains_the_seam_callers_and_tests_patch(self):
        """Moving it broke two suites once already; keep it patchable."""
        with (
            self._config(),
            patch.object(listing, "list_dbs", return_value=["patched"]) as seam,
        ):
            assert listing._rpc_db_exist("patched") is True
            assert seam.called

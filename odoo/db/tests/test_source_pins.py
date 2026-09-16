import ast
import inspect
import pathlib
import textwrap
import typing
import unittest

from odoo.db import (
    bulk,
    cursor,
    lag,
    leaks,
    pool,
    probe,
)
from odoo.libs import breaker

from ._source import _callees, _calls_on, _def_ast, _instance_attrs

_DB_PACKAGE = pathlib.Path(pool.__file__).parent


class TestEveryDsnConsumerExpandsConninfo(unittest.TestCase):
    def test_conninfo_to_dict_is_imported_only_by_dsn(self):
        importers = []
        for path in sorted(_DB_PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names: tuple[str, ...] = ()
                if isinstance(node, ast.ImportFrom):
                    names = tuple(a.name for a in node.names)
                if "conninfo_to_dict" in names:
                    importers.append(path.name)
        self.assertEqual(importers, ["dsn.py"])


class TestSchemaCacheClearsHaveDistinctCallSites(unittest.TestCase):
    def test_ddl_invalidation_keeps_the_lock_ledger(self):
        self.assertEqual(
            _calls_on(cursor.Cursor.invalidate_cached_plans, "_schema_cache"),
            {"invalidate_catalog_facts"},
            "DDL does not end the transaction, so the ROW EXCLUSIVE lock this "
            "cursor already took is still held",
        )

    def test_transaction_boundaries_clear_everything(self):
        self.assertEqual(
            _calls_on(cursor.Cursor._reset_transaction_caches, "_schema_cache"),
            {"clear"},
        )
        for method in ("commit", "_rollback"):
            with self.subTest(method=method):
                self.assertIn(
                    "_reset_transaction_caches",
                    _callees(getattr(cursor.Cursor, method)),
                    "both transaction boundaries forget the transaction-scoped "
                    "caches through the one helper, so a cache added there is "
                    "forgotten at both",
                )
                self.assertEqual(
                    _calls_on(getattr(cursor.Cursor, method), "_schema_cache"),
                    set(),
                )

    def test_savepoint_rollback_releases_exactly_the_tables_the_savepoint_locked(self):
        self.assertEqual(
            _calls_on(cursor.Cursor._on_rollback_to_savepoint, "_schema_cache"),
            {"release_locks_since_depth"},
            "the lock ledger and the catalog facts for tables locked at or "
            "after this savepoint's depth are released together, per table, "
            "regardless of whether this cursor issued DDL: dropping the real "
            "PostgreSQL lock is what makes a foreign session's DDL visible, "
            "not this cursor's own _schema_changed flag",
        )
        source = textwrap.dedent(
            inspect.getsource(cursor.Cursor._on_rollback_to_savepoint)
        )
        guards = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.If) and "_schema_changed" in ast.unparse(node.test)
        ]
        self.assertEqual(
            len(guards),
            0,
            "no _schema_changed-gated branch left: the release is "
            "unconditional and scoped by savepoint depth instead",
        )


class TestCursorSatisfiesItsMixinContracts(unittest.TestCase):
    def _protocol_members(self, name):
        source = inspect.getsource(bulk)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                return {n.name for n in node.body if isinstance(n, ast.FunctionDef)} | {
                    t.target.id
                    for t in node.body
                    if isinstance(t, ast.AnnAssign) and isinstance(t.target, ast.Name)
                }
        raise AssertionError(f"{name} not found in odoo.db.bulk")

    def test_cursor_provides_every_bulk_host_member(self):
        required = self._protocol_members("_CursorInternals")
        self.assertTrue(required, "the Protocol declared nothing — check the parse")
        provided = (
            set(dir(cursor.Cursor))
            | set(cursor.Cursor.__annotations__)
            | _instance_attrs(cursor.Cursor)
            | _instance_attrs(cursor.BaseCursor)
        )
        self.assertEqual(sorted(required - provided), [])


class TestSchemaChangeDrainsAtCommit(unittest.TestCase):
    def test_ddl_arms_the_flag_rather_than_draining_inline(self):
        src = inspect.getsource(cursor.Cursor._invalidate_caches_after_ddl)
        self.assertIn("_schema_changed", src)
        self.assertNotIn(
            "_drain_sibling_connections",
            src,
            "draining per statement closes and reopens every idle connection "
            "once per DDL statement — ~1000 times during a module install — "
            "and an uncommitted schema change is invisible to the connections "
            "it would be healing.",
        )

    def test_commit_is_the_only_thing_that_drains(self):
        self.assertIn(
            "_drain_sibling_connections",
            _callees(cursor.Cursor.commit),
            "commit is the moment the schema change becomes visible to other "
            "connections, so it is the moment they must be drained",
        )
        for name in ("_rollback", "_on_rollback_to_savepoint", "_close"):
            with self.subTest(method=name):
                self.assertNotIn(
                    "_drain_sibling_connections",
                    _callees(getattr(cursor.Cursor, name)),
                    f"{name} must not drain: nothing it undoes ever became "
                    f"visible to another connection",
                )

    def test_rollback_disarms_the_flag(self):
        self.assertIn(
            "_schema_changed",
            _instance_attrs(cursor.Cursor),
            "the flag must be reset on rollback, or a rolled-back schema "
            "change drains on the next unrelated commit",
        )
        self.assertIn("_schema_changed", inspect.getsource(cursor.Cursor._rollback))


class TestEveryCheckoutIsTracked(unittest.TestCase):
    def test_the_leak_warning_uses_its_own_throttle(self):
        names = _callees(pool.ConnectionPool._warn_about_leaks)
        self.assertIn("acquire_report_interval", names)
        self.assertNotIn(
            "_reaper",
            names,
            "sharing the reaper's slot would let a leak warning silence a sweep",
        )


class TestPipelineModeCannotBypassTheFailureSeam(unittest.TestCase):
    def test_the_pipeline_exit_routes_the_deferred_error_through_the_seam(self):
        self.assertIn(
            "_statement_failed",
            _callees(cursor.Cursor.pipeline),
            "the ExitStack exit is where psycopg finally raises a pipelined "
            "statement's error; nothing else can hand it to the seam",
        )

    def test_it_only_takes_errors_that_reached_the_server(self):
        self.assertIn(
            "has_reached_server",
            _callees(cursor.Cursor.pipeline),
            "the same except also sees whatever the caller's block raised; a "
            "plain Python error carries no SQLSTATE and is not the seam's",
        )

    def test_only_the_outermost_block_hooks_the_sync(self):
        fn = _def_ast(inspect.getsource(inspect.unwrap(cursor.Cursor.pipeline)))
        nested = next(node for node in fn.body if isinstance(node, ast.If))
        self.assertNotIn(
            "_statement_failed",
            {
                node.func.attr
                for node in ast.walk(nested)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            },
            "a nested block syncs nothing, so it can observe no deferred error",
        )

    def test_the_seam_short_circuits_before_it_does_any_work(self):
        fn = _def_ast(inspect.getsource(cursor.Cursor._statement_failed))
        body = [n for n in fn.body if not isinstance(n, ast.Expr)]
        self.assertIsInstance(
            body[0],
            ast.If,
            "the idempotence check must be the first thing the seam does",
        )
        guard = typing.cast("ast.If", body[0])
        self.assertIsInstance(
            guard.test,
            ast.Call,
            "the guard must be the bare question, not a condition that can be "
            "disabled beside it",
        )
        self.assertEqual(
            getattr(typing.cast("ast.Call", guard.test).func, "id", None),
            "is_handled_by_seam",
            "the guard must be the bare question, not a condition that can be "
            "disabled beside it",
        )
        self.assertIsInstance(
            guard.body[-1], ast.Return, "the check must actually short-circuit"
        )
        self.assertIn(
            "mark_handled_by_seam",
            _callees(cursor.Cursor._statement_failed),
            "a seam that never marks can never short-circuit",
        )

    def test_execute_values_carries_no_seam_of_its_own(self):
        called = _callees(bulk._BulkAccessMixin.execute_values)
        self.assertNotIn(
            "_log_sql_error",
            called,
            "logging alone was a third of the seam: it left the stale-plan "
            "mark off every pipelined execute_values, and the ORM's bulk "
            "writers reach this path",
        )
        self.assertNotIn(
            "_statement_failed",
            called,
            "every statement execute_values issues goes through self.execute, "
            "whose own except is the seam, and a deferred pipelined error "
            "surfaces at the exit of the self.pipeline() block it opened; a "
            "third call here only ever short-circuited on the mark (measured: "
            "both paths logged cursor.statement_seam_short_circuit)",
        )
        self.assertEqual(
            {"execute", "pipeline"} & called,
            {"execute", "pipeline"},
            "the two entry points that carry the seam on its behalf",
        )


class TestTheBreakerLockIsNotReentrant(unittest.TestCase):
    def test_allow_does_not_go_through_the_property(self):
        self.assertNotIn(
            "closed",
            _callees(breaker.CircuitBreaker.acquire_attempt),
            "the lock-held path must read _open directly",
        )

    def test_the_cooldown_maths_exists_once(self):
        members = {
            "cooldown_remaining": typing.cast(
                "property", breaker.CircuitBreaker.__dict__["cooldown_remaining"]
            ).fget,
            "get_snapshot": breaker.CircuitBreaker.get_snapshot,
        }
        for name, fn in members.items():
            with self.subTest(method=name):
                self.assertIn(
                    "_get_cooldown_remaining_locked",
                    _callees(fn),
                    "two copies of the same expression drifted apart once "
                    "already in this package",
                )

    def test_the_locked_helper_does_not_take_the_lock(self):
        self.assertNotIn(
            "_lock",
            _callees(breaker.CircuitBreaker._get_cooldown_remaining_locked),
            "it is called from inside the lock; taking it again deadlocks",
        )


class TestThePairedGaugesArePublishedTogether(unittest.TestCase):
    def test_recording_a_lag_sample_takes_the_lock(self):
        self.assertIn("_lock", _callees(lag.ReplicaLagGate.record))

    def test_rendering_them_takes_it_too(self):
        self.assertIn("_lock", _callees(lag.ReplicaLagGate.get_snapshot))

    def test_the_per_cursor_read_stays_lock_free(self):
        self.assertNotIn(
            "_lock",
            _callees(lag.ReplicaLagGate.is_replica_usable),
            "is_replica_usable() runs per read-only cursor and reads ONE flag; a single "
            "bool is never torn and the pair has its own guarded readers",
        )

    def test_the_leak_throttle_owns_a_lock(self):
        self.assertIn(
            "_report_lock", _callees(leaks.CheckoutTracker.acquire_report_interval)
        )

    def test_tracking_and_release_stay_lock_free(self):
        for name in ("track", "release"):
            with self.subTest(method=name):
                self.assertNotIn(
                    "_report_lock",
                    _callees(getattr(leaks.CheckoutTracker, name)),
                    "single dict operations; the throttle's lock is not theirs",
                )


class TestTheSaturationErrorReadsOneConsistentPair(unittest.TestCase):
    def test_both_counters_come_from_one_acquisition(self):
        src = inspect.getsource(pool.ConnectionPool._prepare_budget_exhausted_error)
        self.assertIn("with self._lock:", src)
        head, _, tail = src.partition("with self._lock:")
        self.assertNotIn("len(self._pools)", head)
        self.assertNotIn("self._direct_out", head)
        body = tail[: tail.index("return PoolError")]
        self.assertIn("len(self._pools)", body)
        self.assertIn("self._direct_out", body)


class TestNoSelfLockIsTakenTwice(unittest.TestCase):
    LOCKED_CLASSES = (
        pool.ConnectionPool,
        probe.ReachabilityProbe,
        breaker.CircuitBreaker,
        lag.ReplicaLagGate,
    )

    @staticmethod
    def _takes_self_lock(node) -> bool:
        for sub in ast.walk(node):
            if not isinstance(sub, ast.With):
                continue
            for item in sub.items:
                ctx = item.context_expr
                if (
                    isinstance(ctx, ast.Attribute)
                    and ctx.attr.endswith("lock")
                    and isinstance(ctx.value, ast.Name)
                    and ctx.value.id == "self"
                ):
                    return True
        return False

    @staticmethod
    def _self_calls_inside_locks(node) -> set[str]:
        found = set()
        for sub in ast.walk(node):
            if not isinstance(sub, ast.With):
                continue
            locked = any(
                isinstance(i.context_expr, ast.Attribute)
                and i.context_expr.attr.endswith("lock")
                for i in sub.items
            )
            if not locked:
                continue
            for reached in ast.walk(ast.Module(body=sub.body, type_ignores=[])):
                if (
                    isinstance(reached, ast.Attribute)
                    and isinstance(reached.value, ast.Name)
                    and reached.value.id == "self"
                ):
                    found.add(reached.attr)
        return found

    def test_no_method_called_under_a_lock_takes_that_lock(self):
        for cls in self.LOCKED_CLASSES:
            tree = _def_ast(inspect.getsource(cls))
            methods = {
                n.name: n
                for n in tree.body
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            }
            called_under_lock = set()
            for node in methods.values():
                called_under_lock |= self._self_calls_inside_locks(node)
            for name in sorted(called_under_lock & methods.keys()):
                with self.subTest(cls=cls.__name__, method=name):
                    self.assertFalse(
                        self._takes_self_lock(methods[name]),
                        f"{cls.__name__}.{name} is called from inside a "
                        f"`with self._lock:` block and takes the lock itself; "
                        f"threading.Lock is not reentrant, so that hangs",
                    )

    def test_the_check_can_see_a_violation(self):
        src = textwrap.dedent("""
            class Bad:
                def outer(self):
                    with self._lock:
                        if self.prop:          # a property READ, not a call
                            return self.inner()

                @property
                def prop(self):
                    with self._lock:
                        return True

                def inner(self):
                    with self._lock:
                        return 1
        """)
        tree = _def_ast(src)
        methods = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        under_lock = self._self_calls_inside_locks(methods["outer"])
        for name in ("inner", "prop"):
            with self.subTest(reached_as=name):
                self.assertIn(name, under_lock)
                self.assertTrue(self._takes_self_lock(methods[name]))


if __name__ == "__main__":
    unittest.main()


class TestThePackageImportsOnlyWhatItMayDependOn(unittest.TestCase):
    # The `db-imports-only-libs` layer contract that went with tooling/ on
    # 2026-09-11: the package may depend on the standard library, psycopg,
    # odoo.libs, odoo.exceptions and odoo.release -- never on odoo.tools, the
    # ORM, or anything that would drag the framework in behind a cursor.
    _ALLOWED_ODOO = ("odoo.libs", "odoo.exceptions", "odoo.release", "odoo.db")

    @staticmethod
    def _imports_of(path: pathlib.Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        guarded = {
            id(child)
            for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and getattr(node.test, "id", None) == "TYPE_CHECKING"
            for child in ast.walk(node)
        }
        found: set[str] = set()
        for node in ast.walk(tree):
            if id(node) in guarded:
                continue
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module)
        return found

    def test_no_module_reaches_past_libs(self):
        package = pathlib.Path(cursor.__file__).parent
        offenders = {}
        for path in sorted(package.glob("*.py")):
            bad = sorted(
                name
                for name in self._imports_of(path)
                if name.startswith("odoo") and not name.startswith(self._ALLOWED_ODOO)
            )
            if bad:
                offenders[path.name] = bad
        self.assertEqual(offenders, {})

    # `db-resilience-below-connectivity` (doc/architecture/module.md): the
    # resilience tier must be importable with no pool and no cursor behind it.
    _RESILIENCE = ("lag", "budget", "leaks", "reaper", "probe", "metrics", "stats")
    _CONNECTIVITY = (
        "pool",
        "cursor",
        "ddl",
        "schema",
        "savepoint",
        "schema_cache",
        "bulk",
        "lifecycle",
        "endpoints",
        "replica",
    )

    def test_the_resilience_tier_sits_below_connectivity(self):
        package = pathlib.Path(cursor.__file__).parent
        offenders = {}
        for name in self._RESILIENCE:
            tree = ast.parse((package / f"{name}.py").read_text(encoding="utf-8"))
            reached = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                    reached.add(node.module.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("odoo.db."):
                        reached.add(node.module.split(".")[2])
            bad = sorted(reached & set(self._CONNECTIVITY))
            if bad:
                offenders[name] = bad
        self.assertEqual(offenders, {})

    def test_the_scan_sees_a_runtime_reach_and_spares_a_type_checking_one(self):
        source = (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n    from odoo.orm.runtime import Transaction\n"
            "import odoo.tools\n"
        )
        path = pathlib.Path(self.id() + ".py")
        path.write_text(source, encoding="utf-8")
        self.addCleanup(path.unlink)
        self.assertEqual(self._imports_of(path), {"typing", "odoo.tools"})

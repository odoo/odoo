import logging
import math
from collections import defaultdict
from datetime import datetime

from psycopg.errors import UntranslatableCharacter

from odoo import fields, models
from odoo.fields import Command
from odoo.libs.lru import LRU
from odoo.orm.model_test_env import (
    InMemoryRecordRulesNotSupported,
    InMemorySqlNotSupported,
    ModelRegistry,
    model_test_env,
)
from odoo.orm.models.metaclass import MetaModel
from odoo.tests import TransactionCase, tagged

from odoo.addons.test_orm.models.test_orm import (
    CalendarTest,
    TestOrmAutovacuumed,
    TestOrmCategory,
    TestOrmCompany,
    TestOrmFoo,
    TestOrmModel_A,
    TestOrmModel_B,
    TestOrmMove,
    TestOrmMove_Line,
    TestOrmMultiTag,
    TestOrmPayment,
    TestOrmRelated_Translation_1,
)

_logger = logging.getLogger(__name__)

_STUB_MODULE = "test_orm_diff_stub"


class _StubIrModelData(models.Model):
    _name = "ir.model.data"
    _module = _STUB_MODULE
    _description = "ir.model.data (differential test stub)"
    _log_access = False

    module = fields.Char()
    name = fields.Char()
    model = fields.Char()
    res_id = fields.Integer()
    noupdate = fields.Boolean()


class _StubIrAttachment(models.Model):
    _name = "ir.attachment"
    _module = _STUB_MODULE
    _description = "ir.attachment (differential test stub)"
    _log_access = False

    res_model = fields.Char()
    res_field = fields.Char()
    res_id = fields.Integer()


class _StubPartner(models.Model):
    _name = "res.partner"
    _module = _STUB_MODULE
    _description = "Partner (differential test stub)"
    _log_access = False


class _StubCompanyDefault(models.AbstractModel):
    _name = "ir.default"
    _module = _STUB_MODULE
    _description = "Company default (differential test stub)"

    def _get_model_defaults(self, model_name):
        return {"date": "2026-09-11"} if model_name == "test_orm.company" else {}


class _StubJsonDiscussion(models.Model):
    _name = "test_orm.discussion"
    _module = _STUB_MODULE
    _description = "JSON field boundary (differential test fixture)"
    _log_access = False

    name = fields.Char()
    history = fields.Json()


def _isolated_registry(*classes):
    saved = MetaModel._module_to_models__
    try:
        MetaModel._module_to_models__ = defaultdict(list)
        registry = ModelRegistry([*classes, _StubIrModelData, _StubIrAttachment])
    finally:
        MetaModel._module_to_models__ = saved
    registry.ormcache_lrus = defaultdict(lambda: LRU(4096))
    return registry


@tagged("post_install", "-at_install")
class TestBackendDifferential(TransactionCase):
    def _diff(self, classes, script, msg=""):
        registry = _isolated_registry(*classes)
        with model_test_env(registry=registry) as env_a:
            obs_a = script(env_a)
        obs_b = script(self.env)
        self.assertEqual(
            obs_a,
            obs_b,
            f"DB-free harness diverged from SQL backend{': ' + msg if msg else ''}\n"
            f"  harness (side A): {obs_a!r}\n"
            f"  SQL     (side B): {obs_b!r}",
        )
        return obs_a

    def test_create_read_defaults_and_falsy(self):
        def script(env):
            F = env["test_orm.foo"]
            F.create({"name": "falsy", "value1": 0, "value2": 0, "text": ""})
            F.create({"name": "filled", "value1": 7, "value2": -3, "text": "hi"})
            F.create({"name": "defaulted"})
            env.flush_all()
            env.invalidate_all()
            recs = F.search(
                [("name", "in", ["falsy", "filled", "defaulted"])], order="name"
            )
            return [
                {
                    "name": r.name,
                    "value1": r.value1,
                    "value2": r.value2,
                    "text": r.text,
                    "text_is_falsy": not r.text,
                }
                for r in recs
            ]

        self._diff((TestOrmFoo,), script, "create defaults / falsy round-trip")

    def test_jsonb_cold_reads_preserve_numbers_and_ownership(self):
        def script(env):
            record = env["test_orm.discussion"].create(
                {
                    "name": "JSON cold read",
                    "history": {"large": 1e20, "zero": -0.0, "nested": [{"a": 1}]},
                }
            )
            env.flush_all()
            env.invalidate_all()
            value = record.history
            self.assertIs(type(value["large"]), int)
            self.assertEqual(value["large"], 100000000000000000000)
            self.assertEqual(math.copysign(1, value["zero"]), 1)
            value["nested"][0]["a"] = 99
            self.assertEqual(record.history["nested"][0]["a"], 1)
            env.invalidate_all()
            return record.history

        self._diff((_StubJsonDiscussion,), script)

    def test_jsonb_rejects_nul_in_public_writes(self):
        values = {"name": "JSON NUL", "history": {"nested": ["\0"]}}
        with self.assertRaises(UntranslatableCharacter), self.cr.savepoint():
            self.env["test_orm.discussion"].create(values)
        with model_test_env(registry=_isolated_registry(_StubJsonDiscussion)) as env:
            with self.assertRaises(UntranslatableCharacter):
                env["test_orm.discussion"].create(values)

    def test_unicode_ilike_uses_character_case_mapping(self):
        def script(env):
            records = env["test_orm.foo"].create(
                [{"name": name} for name in ("ΟΣ", "οσ", "ος", "Σ", "σ", "ς")]
            )
            env.flush_all()
            result = []
            for operator in ("=ilike", "ilike"):
                for pattern in ("ΟΣ", "οσ", "ος", "%Σ", "%σ", "%ς", "__"):
                    domain = [("name", operator, pattern)]
                    selected = records.search([("id", "in", records.ids), *domain])
                    expected = sorted(selected.mapped("name"))
                    actual = sorted(records.filtered_domain(domain).mapped("name"))
                    self.assertEqual(actual, expected, (operator, pattern))
                    result.append(actual)
            return result

        self._diff((TestOrmFoo,), script)

    def test_unicode_ilike_uses_the_database_unicode_version(self):
        names = [
            "\ua7ce",
            "\ua7cf",
            "\ua7d2",
            "\ua7d3",
            "\ua7d4",
            "\ua7d5",
            "\U00010400",
            "\U00010428",
        ]
        records = self.env["test_orm.foo"].create([{"name": name} for name in names])
        self.env.flush_all()
        for operator in ("=ilike", "ilike"):
            for pattern in names:
                domain = [("name", operator, pattern)]
                expected = records.search([("id", "in", records.ids), *domain])
                self.assertEqual(
                    set(records.filtered_domain(domain).ids),
                    set(expected.ids),
                    (operator, pattern),
                )

    def test_boolean_default_true(self):
        def script(env):
            move = env["test_orm.move"].create(
                {"line_ids": [Command.create({"quantity": 4})]}
            )
            env.flush_all()
            env.invalidate_all()
            line = move.line_ids
            return {"visible": line.visible, "quantity": line.quantity}

        self._diff(
            (TestOrmMove, TestOrmMove_Line, TestOrmMultiTag, TestOrmPayment),
            script,
            "Boolean default=True round-trip",
        )

    def test_write_roundtrip(self):
        def script(env):
            r = env["test_orm.foo"].create({"name": "a", "value1": 1})
            r.write({"name": "b", "value1": 2, "value2": 9})
            env.flush_all()
            env.invalidate_all()
            return {"name": r.name, "value1": r.value1, "value2": r.value2}

        self._diff((TestOrmFoo,), script, "write round-trip")

    def test_write_does_not_create_missing_rows(self):
        def script(env):
            model = env["test_orm.foo"]
            present = model.create({"name": "present", "value1": 1})
            missing = model.browse(987654321)
            (present + missing).write({"value1": 17})
            env.flush_all()
            env.invalidate_all()
            return present.value1, bool(missing.exists())

        self.assertEqual(self._diff((TestOrmFoo,), script), (17, False))

    def test_exact_patterns_match_the_entire_string(self):
        def script(env):
            values = ["abc", "abc\n", "abcd", "猫", "猫\n", "a%b", "a_b"]
            records = env["test_orm.foo"].create([{"text": value} for value in values])
            result = {}
            for operator in ("=like", "=ilike", "not =like", "not =ilike"):
                for pattern in ("abc", "猫", "_", r"a\%b", r"a\_b"):
                    domain = [("text", operator, pattern)]
                    filtered = records.filtered_domain(domain).mapped("text")
                    searched = records.search(
                        [("id", "in", records.ids), *domain], order="id"
                    ).mapped("text")
                    self.assertEqual(filtered, searched, (operator, pattern))
                    result[operator, pattern] = filtered
            return result

        observed = self._diff((TestOrmFoo,), script)
        self.assertEqual(observed["=like", "abc"], ["abc"])
        self.assertEqual(
            observed["not =like", "猫"], ["abc", "abc\n", "abcd", "猫\n", "a%b", "a_b"]
        )

    def test_like_patterns_preserve_trailing_escape_semantics(self):
        def script(env):
            values = [
                "a",
                "a%",
                "a%x",
                "xa%",
                "A%",
                "%",
                "x%",
                "a\\",
                "a\\x",
                "a\\%",
                "猫%",
                "a%\n",
            ]
            records = env["test_orm.foo"].create([{"text": value} for value in values])
            result = {}
            for operator in ("like", "ilike", "not like", "not ilike"):
                for pattern in (
                    "a\\",
                    "\\",
                    "猫\\",
                    "a\\\\",
                    "a\\\\\\",
                    "a\\%",
                    "a\\_",
                ):
                    domain = [("text", operator, pattern)]
                    filtered = records.filtered_domain(domain).mapped("text")
                    searched = records.search(
                        [("id", "in", records.ids), *domain], order="id"
                    ).mapped("text")
                    self.assertEqual(filtered, searched, (operator, pattern))
                    result[operator, pattern] = filtered
            return result

        observed = self._diff((TestOrmFoo,), script)
        self.assertEqual(observed["like", "a\\"], ["a%", "xa%"])
        self.assertEqual(observed["like", "a\\\\"], ["a\\", "a\\x", "a\\%"])

    def test_column_fetch_excludes_rows_missing_from_a_resolved_query(self):
        def script(env):
            model = env["test_orm.foo"]
            present, removed = model.create([{"name": "present"}, {"name": "removed"}])
            missing = model.browse(987654321)
            records = present + missing + removed
            query = records._as_query(ordered=False)
            removed.unlink()
            env.flush_all()
            fetched = model._fetch_query(query, [model._fields["name"]])
            without_columns = model._fetch_query(query, [])
            return (
                fetched == present,
                missing in fetched,
                removed in fetched,
                without_columns == records,
            )

        self.assertEqual(self._diff((TestOrmFoo,), script), (True, False, False, True))

    def test_company_values_survive_flush_and_company_switches(self):
        def snapshot(record):
            return (
                record.foo,
                record.count,
                record.truth,
                record.phi,
                str(record.date),
                record.tag_id.name,
            )

        def script(env):
            tag = env["test_orm.multi.tag"].create({"name": "company tag"})
            record = env["test_orm.company"].create(
                {
                    "foo": "alpha",
                    "count": 3,
                    "truth": True,
                    "phi": 1.25,
                    "date": "2026-09-11",
                    "tag_id": tag.id,
                }
            )
            warm = snapshot(record)
            env.flush_all()
            env.invalidate_all()
            cold = snapshot(record)
            self.assertEqual(cold, warm)
            other = env["res.company"].create({"name": "ORM other company"})
            second = record.with_company(other)
            fallback = snapshot(second)
            second.write(
                {
                    "foo": "beta",
                    "count": 7,
                    "truth": False,
                    "phi": 2.5,
                    "date": False,
                    "tag_id": False,
                }
            )
            env.flush_all()
            env.invalidate_all()
            return warm, cold, fallback, snapshot(record), snapshot(second)

        self.env["ir.default"].set("test_orm.company", "date", "2026-09-11")
        sql = self._diff(
            (TestOrmCompany, TestOrmMultiTag, _StubPartner, _StubCompanyDefault), script
        )
        self.assertEqual(sql[0], ("alpha", 3, True, 1.25, "2026-09-11", "company tag"))
        self.assertEqual(sql[2], (False, 0, False, 0.0, "2026-09-11", False))
        self.assertEqual(sql[3], sql[0])
        self.assertEqual(sql[4], ("beta", 7, False, 2.5, "False", False))

    def test_unlink(self):
        def script(env):
            F = env["test_orm.foo"]
            a = F.create({"name": "a"})
            F.create({"name": "b"})
            c = F.create({"name": "c"})
            (a + c).unlink()
            env.flush_all()
            env.invalidate_all()
            return sorted(F.search([]).mapped("name"))

        self._diff((TestOrmFoo,), script, "unlink")

    def _make_foos(self, env, rows):
        F = env["test_orm.foo"]
        for name, v1 in rows:
            F.create({"name": name, "value1": v1})
        env.flush_all()
        env.invalidate_all()
        return F

    def test_search_equality_operators(self):
        rows = [("alpha", 1), ("beta", 2), ("gamma", 3), ("delta", 2)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "eq": sorted(F.search([*scope, ("value1", "=", 2)]).mapped("name")),
                "ne": sorted(F.search([*scope, ("value1", "!=", 2)]).mapped("name")),
                "in": sorted(
                    F.search([*scope, ("value1", "in", [1, 3])]).mapped("name")
                ),
                "not_in": sorted(
                    F.search([*scope, ("value1", "not in", [1, 3])]).mapped("name")
                ),
                "name_eq": sorted(
                    F.search([*scope, ("name", "=", "beta")]).mapped("name")
                ),
                "name_false": sorted(
                    F.search([*scope, ("name", "!=", False)]).mapped("name")
                ),
            }

        self._diff((TestOrmFoo,), script, "= / != / in / not in")

    def test_search_comparison_operators(self):
        rows = [("a", 1), ("b", 2), ("c", 3), ("d", 4)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "lt": sorted(F.search([*scope, ("value1", "<", 3)]).mapped("name")),
                "le": sorted(F.search([*scope, ("value1", "<=", 3)]).mapped("name")),
                "gt": sorted(F.search([*scope, ("value1", ">", 2)]).mapped("name")),
                "ge": sorted(F.search([*scope, ("value1", ">=", 2)]).mapped("name")),
            }

        self._diff((TestOrmFoo,), script, "< / <= / > / >=")

    def test_search_like_ilike_ascii(self):
        rows = [("Apple", 0), ("apricot", 0), ("Banana", 0), ("grApe", 0)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "like_ap": sorted(
                    F.search([*scope, ("name", "like", "ap")]).mapped("name")
                ),
                "ilike_ap": sorted(
                    F.search([*scope, ("name", "ilike", "ap")]).mapped("name")
                ),
                "not_like": sorted(
                    F.search([*scope, ("name", "not like", "an")]).mapped("name")
                ),
                "ilike_a": sorted(
                    F.search([*scope, ("name", "ilike", "a")]).mapped("name")
                ),
            }

        self._diff((TestOrmFoo,), script, "like / ilike (ASCII)")

    def test_search_order_asc_desc(self):
        rows = [("a", 3), ("b", 1), ("c", 2)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "asc": F.search(scope, order="value1 asc").mapped("name"),
                "desc": F.search(scope, order="value1 desc").mapped("name"),
            }

        self._diff((TestOrmFoo,), script, "order asc/desc")

    def test_search_order_multikey(self):
        rows = [("a", 2), ("b", 1), ("c", 2), ("d", 1)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "multi": F.search(scope, order="value1 asc, name desc").mapped("name"),
            }

        self._diff((TestOrmFoo,), script, "multi-key order")

    def test_search_order_nulls(self):
        def script(env):
            F = env["test_orm.foo"]
            F.create({"name": "b"})
            F.create({})
            F.create({"name": "a"})
            env.flush_all()
            env.invalidate_all()
            return {
                "asc": F.search([], order="name asc").mapped("name"),
                "desc": F.search([], order="name desc").mapped("name"),
            }

        self._diff((TestOrmFoo,), script, "NULLS ordering")

    def test_search_limit_offset(self):
        rows = [(f"n{i}", i) for i in range(6)]
        names = [n for n, _ in rows]

        def script(env):
            F = self._make_foos(env, rows)
            scope = [("name", "in", names)]
            return {
                "limit": F.search(scope, order="value1", limit=3).mapped("name"),
                "offset": F.search(scope, order="value1", offset=2).mapped("name"),
                "both": F.search(scope, order="value1", limit=2, offset=3).mapped(
                    "name"
                ),
                "count": F.search_count(scope),
            }

        self._diff((TestOrmFoo,), script, "limit / offset / count")

    def test_m2m_set_link_unlink(self):
        def script(env):
            A = env["test_orm.model_a"]
            B = env["test_orm.model_b"]
            b1 = B.create({"name": "b1"})
            b2 = B.create({"name": "b2"})
            b3 = B.create({"name": "b3"})
            a = A.create(
                {"name": "a", "a_restricted_b_ids": [Command.set([b1.id, b2.id])]}
            )

            def snap():
                env.flush_all()
                env.invalidate_all()
                return a.a_restricted_b_ids.mapped("name")

            steps = {"after_set": snap()}
            a.write({"a_restricted_b_ids": [Command.link(b3.id)]})
            steps["after_link"] = snap()
            a.write({"a_restricted_b_ids": [Command.unlink(b1.id)]})
            steps["after_unlink"] = snap()
            a.write({"a_restricted_b_ids": [Command.set([b3.id])]})
            steps["after_reset"] = snap()
            a.write({"a_restricted_b_ids": [Command.clear()]})
            steps["after_clear"] = snap()
            return steps

        self._diff(
            (TestOrmModel_A, TestOrmModel_B), script, "m2m link/unlink/set/clear"
        )

    def test_m2m_read_ordering(self):
        def script(env):
            A = env["test_orm.model_a"]
            B = env["test_orm.model_b"]
            b1 = B.create({"name": "b1"})
            b2 = B.create({"name": "b2"})
            b3 = B.create({"name": "b3"})
            a = A.create(
                {
                    "name": "a",
                    "a_restricted_b_ids": [Command.set([b3.id, b1.id, b2.id])],
                }
            )
            env.flush_all()
            env.invalidate_all()
            return a.a_restricted_b_ids.mapped("name")

        self._diff((TestOrmModel_A, TestOrmModel_B), script, "m2m read ordering")

    def test_o2m_commands(self):
        def script(env):
            M = env["test_orm.move"]
            move = M.create(
                {
                    "line_ids": [
                        Command.create({"quantity": 5, "visible": True}),
                        Command.create({"quantity": 3, "visible": True}),
                    ]
                }
            )

            def snap():
                env.flush_all()
                env.invalidate_all()
                return {
                    "lines": sorted(move.line_ids.mapped("quantity")),
                    "quantity": move.quantity,
                }

            steps = {"after_create": snap()}
            first = move.line_ids.sorted("quantity")[0]
            move.write({"line_ids": [Command.update(first.id, {"quantity": 10})]})
            steps["after_update"] = snap()
            move.write({"line_ids": [Command.create({"quantity": 1, "visible": True})]})
            steps["after_add"] = snap()
            biggest = move.line_ids.sorted("quantity")[-1]
            move.write({"line_ids": [Command.delete(biggest.id)]})
            steps["after_delete"] = snap()
            move.write({"line_ids": [Command.clear()]})
            steps["after_clear"] = snap()
            return steps

        self._diff(
            (TestOrmMove, TestOrmMove_Line, TestOrmMultiTag, TestOrmPayment),
            script,
            "o2m Command processing",
        )

    def test_translated_field_en_us_roundtrip(self):
        def script(env):
            M = env["test_orm.related_translation_1"]
            r = M.create({"name": "Hello"})
            env.flush_all()
            env.invalidate_all()
            created = r.name
            r.name = "World"
            env.flush_all()
            env.invalidate_all()
            written = r.name
            found = M.search([("name", "=", "World")]).mapped("name")
            return {"created": created, "written": written, "found": sorted(found)}

        self._diff(
            (TestOrmRelated_Translation_1,), script, "translated en_US round-trip"
        )

    def test_datetime_boundaries(self):
        moments = [
            datetime(2020, 1, 1, 12, 0, 0),
            datetime(2020, 6, 15, 8, 30, 0),
            datetime(2021, 3, 3, 0, 0, 0),
        ]

        def script(env):
            M = env["test_orm.autovacuumed"]
            for m in moments:
                M.create({"expire_at": m})
            env.flush_all()
            env.invalidate_all()
            b = datetime(2020, 6, 15, 8, 30, 0)
            return {
                "lt": M.search_count([("expire_at", "<", b)]),
                "le": M.search_count([("expire_at", "<=", b)]),
                "gt": M.search_count([("expire_at", ">", b)]),
                "ge": M.search_count([("expire_at", ">=", b)]),
                "eq": M.search_count([("expire_at", "=", b)]),
                "order": [
                    dt.isoformat()
                    for dt in M.search([], order="expire_at desc").mapped("expire_at")
                ],
            }

        self._diff((TestOrmAutovacuumed,), script, "datetime boundaries")

    def test_date_boundaries(self):
        from datetime import date

        dates = [date(2020, 1, 1), date(2020, 6, 15), date(2021, 3, 3)]

        def script(env):
            M = env["calendar.test"]
            for d in dates:
                M.create({"x_date_start": d})
            env.flush_all()
            env.invalidate_all()
            b = date(2020, 6, 15)
            return {
                "lt": M.search_count([("x_date_start", "<", b)]),
                "ge": M.search_count([("x_date_start", ">=", b)]),
                "eq": M.search_count([("x_date_start", "=", b)]),
                "order": [
                    d.isoformat()
                    for d in M.search([], order="x_date_start").mapped("x_date_start")
                ],
            }

        self._diff((CalendarTest,), script, "date boundaries")

    def test_divergence_record_rules_not_enforced(self):
        registry = _isolated_registry(TestOrmFoo)
        with model_test_env(registry=registry) as env_a:
            self.assertFalse(env_a.backend.supports_record_rules)
            with self.assertRaises(InMemoryRecordRulesNotSupported):
                _ = env_a["ir.rule"]
        self.assertTrue(self.env.backend.supports_record_rules)
        self.assertIn("ir.rule", self.env.registry)

    def test_divergence_raw_sql_fails_loud(self):
        registry = _isolated_registry(TestOrmFoo)
        with model_test_env(registry=registry) as env_a:
            with self.assertRaises(InMemorySqlNotSupported):
                env_a.cr.execute('SELECT count(*) FROM "test_orm_foo"')
        self.env["test_orm.foo"].create({"name": "x"})
        self.env.flush_all()
        self.env.cr.execute('SELECT count(*) FROM "test_orm_foo"')
        self.assertGreaterEqual(self.env.cr.fetchone()[0], 1)

    def test_divergence_rollback_and_savepoint_fail_loud(self):
        registry = _isolated_registry(TestOrmFoo)
        with model_test_env(registry=registry) as env_a:
            with self.assertRaises(InMemorySqlNotSupported):
                env_a.cr.rollback()
            # a savepoint snapshots the dict storage; both backends forget "temp"
            sp_a = env_a.cr.savepoint()
            env_a["test_orm.foo"].create({"name": "temp"})
            sp_a.close(rollback=True)
            self.assertFalse(env_a["test_orm.foo"].search([("name", "=", "temp")]))
        F = self.env["test_orm.foo"]
        sp = self.env.cr.savepoint()
        F.create({"name": "temp"})
        sp.close(rollback=True)
        self.assertFalse(F.search([("name", "=", "temp")]))

    def test_divergence_ilike_unaccent(self):
        if not self.env.registry.has_unaccent:
            self.skipTest("unaccent extension not installed")

        def script(env):
            F = env["test_orm.foo"]
            F.create({"name": "Café"})
            F.create({"name": "Cafe"})
            env.flush_all()
            env.invalidate_all()
            scope = [("name", "in", ["Café", "Cafe"])]
            return sorted(F.search([*scope, ("name", "ilike", "cafe")]).mapped("name"))

        registry = _isolated_registry(TestOrmFoo)
        with model_test_env(registry=registry) as env_a:
            obs_a = script(env_a)
        obs_b = script(self.env)
        self.assertEqual(obs_a, ["Cafe"])
        self.assertEqual(obs_b, ["Cafe", "Café"])
        self.assertNotEqual(obs_a, obs_b)

    def test_divergence_parent_store_and_child_of(self):

        def build_tree(env):
            C = env["test_orm.category"]
            root = C.create({"name": "root"})
            child = C.create({"name": "child", "parent": root.id})
            grand = C.create({"name": "grand", "parent": child.id})
            env.flush_all()
            env.invalidate_all()
            return C, root, child, grand

        registry = _isolated_registry(TestOrmCategory)
        with model_test_env(registry=registry) as env_a:
            C_a, root_a, _child_a, grand_a = build_tree(env_a)
            self.assertFalse(grand_a.parent_path)
            with self.assertRaises(TypeError):
                C_a.search([("id", "child_of", root_a.id)])

        C_b, root_b, child_b, grand_b = build_tree(self.env)
        self.assertTrue(grand_b.parent_path)
        self.assertEqual(grand_b.parent_path.count("/"), 3)
        subtree = C_b.search(
            [
                ("id", "child_of", root_b.id),
                ("id", "in", (root_b + child_b + grand_b).ids),
            ]
        )
        self.assertEqual(sorted(subtree.mapped("name")), ["child", "grand", "root"])

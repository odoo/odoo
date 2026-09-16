import datetime
import itertools
import random

from odoo import fields, models
from odoo.orm.model_test_env import ModelRegistry, model_test_env
from odoo.tests import TransactionCase, tagged

from odoo.addons.test_read_group.models import (
    Test_Read_GroupAggregate,
    Test_Read_GroupAggregateMonetary,
    Test_Read_GroupFill_Temporal,
    Test_Read_GroupTag,
    Test_Read_GroupTask,
    Test_Read_GroupUser,
    TestReadGroupAggregateMonetaryRelated,
)

_STUB_MODULE = "test_read_group_matrix_stub"


class _StubPartner(models.Model):
    _name = "res.partner"
    _module = _STUB_MODULE
    _description = "Partner (matrix stub)"
    _log_access = False
    _order = "name"

    name = fields.Char()


class _StubCurrency(models.Model):
    _name = "res.currency"
    _module = _STUB_MODULE
    _description = "Currency (matrix stub)"
    _log_access = False

    name = fields.Char()
    symbol = fields.Char()
    rounding = fields.Float(default=0.01)

    def round(self, amount):
        return round(amount, 2)


class _StubCurrencyRate(models.Model):
    _name = "res.currency.rate"
    _module = _STUB_MODULE
    _description = "Currency rate (matrix stub)"
    _log_access = False

    name = fields.Date()
    rate = fields.Float()
    currency_id = fields.Many2one("res.currency")
    company_id = fields.Many2one("res.company")


class _StubIrModelData(models.Model):
    _name = "ir.model.data"
    _module = _STUB_MODULE
    _description = "ir.model.data (matrix stub)"
    _log_access = False

    module = fields.Char()
    name = fields.Char()
    model = fields.Char()
    res_id = fields.Integer()


def _isolated_registry(*classes):
    return ModelRegistry([*classes, _StubIrModelData], isolated=True)


# the key of a group and the value of an aggregate, spelled so that the two
# tiers compare: a record by its name (ids differ, creation order does not),
# a float exactly; an array keeps its order, which both tiers define
def _spell(value):
    if hasattr(value, "_ids"):
        return tuple(value.mapped("display_name")) if value else ()
    if isinstance(value, list):
        return [_spell(v) for v in value]
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def _rows(model, domain, groupby, aggregates, **kw):
    try:
        rows = model._read_group(domain, groupby, aggregates, **kw)
    except NotImplementedError:
        return NotImplemented
    except ValueError as error:
        return str(error)
    return [tuple(_spell(v) for v in row) for row in rows]


@tagged("post_install", "-at_install")
class TestReadGroupBackendMatrix(TransactionCase):
    maxDiff = None

    def _diff(self, classes, script, msg=""):
        with model_test_env(registry=_isolated_registry(*classes)) as env_a:
            obs_a = script(env_a)
        obs_b = script(self.env)
        suffix = f"in-memory read_group diverged from SQL{': ' + msg if msg else ''}"
        if isinstance(obs_a, dict) and isinstance(obs_b, dict):
            # one call at a time, so the message shows whole rows
            self.assertEqual(list(obs_a), list(obs_b), suffix)
            for key in obs_a:
                self.assertEqual(obs_a[key], obs_b[key], f"{key} -- {suffix}")
        self.assertEqual(obs_a, obs_b, suffix)
        return obs_a

    def test_aggregates_and_groupbys_on_scalars_and_a_many2one(self):
        def script(env):
            Partner = env["res.partner"]
            zulu, alpha = Partner.create([{"name": "zulu"}, {"name": "alpha"}])
            Model = env["test_read_group.aggregate"]
            Model.create(
                [
                    {
                        "key": 1,
                        "value": 5,
                        "numeric_value": 0.1,
                        "partner_id": zulu.id,
                        "display_name": "b",
                    },
                    {
                        "key": 1,
                        "value": 0,
                        "numeric_value": 0.2,
                        "partner_id": alpha.id,
                        "display_name": "a",
                    },
                    {
                        "key": 2,
                        "value": -3,
                        "numeric_value": 0.7,
                        "partner_id": alpha.id,
                        "display_name": False,
                    },
                    {
                        "key": 2,
                        "value": 7,
                        "numeric_value": 0.0,
                        "partner_id": False,
                        "display_name": "",
                    },
                    {
                        "key": 0,
                        "value": 0,
                        "numeric_value": 1.005,
                        "partner_id": False,
                        "display_name": "a",
                    },
                ]
            )
            env.flush_all()
            env.invalidate_all()
            aggregates = [
                "__count",
                "value:sum",
                "value:avg",
                "value:max",
                "value:min",
                "value:count",
                "value:count_distinct",
                "value:array_agg",
                "numeric_value:sum",
                "numeric_value:avg",
                "numeric_value:max",
                "partner_id:count",
                "partner_id:count_distinct",
                "partner_id:recordset",
                "display_name:array_agg_distinct",
                "display_name:count",
                "display_name:count_distinct",
                "display_name:array_agg",
                "id:recordset",
            ]
            groupbys = [
                [],
                ["key"],
                ["partner_id"],
                ["display_name"],
                ["key", "partner_id"],
                ["partner_id", "display_name"],
            ]
            observed = {}
            for groupby in groupbys:
                observed[str(groupby)] = _rows(Model, [], groupby, aggregates)
                for aggregate in ("value:sum", "__count", "numeric_value:sum"):
                    for direction in ("", " desc"):
                        # the groupby keys break the ties an aggregate leaves,
                        # which SQL would otherwise order as the plan happens to
                        order = ", ".join([f"{aggregate}{direction}", *groupby])
                        observed[f"{groupby} order {order}"] = _rows(
                            Model, [], groupby, [aggregate], order=order
                        )
            observed["order outside"] = _rows(
                Model, [], ["key"], ["__count"], order="value:sum desc, key"
            )
            observed["order outside count"] = _rows(
                Model,
                [],
                ["partner_id"],
                ["value:sum"],
                order="__count desc, partner_id",
            )
            observed["having"] = _rows(
                Model, [], ["key"], ["value:sum"], having=[("value:sum", ">", 0)]
            )
            observed["having count"] = _rows(
                Model, [], ["partner_id"], ["__count"], having=[("__count", ">=", 2)]
            )
            observed["limit"] = _rows(
                Model, [], ["key"], ["__count"], order="key desc", limit=2, offset=1
            )
            observed["domain"] = _rows(
                Model, [("partner_id.name", "=", "alpha")], ["key"], ["value:sum"]
            )
            observed["falsy key"] = _rows(
                Model, [("display_name", "=", False)], ["key"], ["__count"]
            )
            return observed

        self._diff((Test_Read_GroupAggregate, _StubPartner), script)

    def test_date_and_datetime_granularities(self):
        def script(env):
            Model = env["test_read_group.fill_temporal"]
            Model.create(
                [
                    {
                        "date": "2026-01-15",
                        "datetime": "2026-01-15 23:30:00",
                        "value": 1,
                    },
                    {
                        "date": "2026-01-16",
                        "datetime": "2026-01-16 03:00:00",
                        "value": 2,
                    },
                    {
                        "date": "2026-03-01",
                        "datetime": "2026-03-01 00:00:00",
                        "value": 4,
                    },
                    {
                        "date": "2026-03-31",
                        "datetime": "2026-03-31 12:00:00",
                        "value": 8,
                    },
                    {
                        "date": "2026-12-31",
                        "datetime": "2026-12-31 23:59:59",
                        "value": 16,
                    },
                    {"date": False, "datetime": False, "value": 32},
                ]
            )
            env.flush_all()
            env.invalidate_all()
            observed = {}
            granularities = (
                "day",
                "week",
                "month",
                "quarter",
                "year",
                "day_of_week",
                "day_of_month",
                "day_of_year",
                "iso_week_number",
                "month_number",
                "quarter_number",
                "year_number",
            )
            for fname, granularity in itertools.product(
                ("date", "datetime"), granularities
            ):
                spec = f"{fname}:{granularity}"
                observed[spec] = _rows(Model, [], [spec], ["value:sum"])
                observed[f"{spec} desc"] = _rows(
                    Model, [], [spec], ["value:sum"], order=f"{spec} desc"
                )
            for granularity in ("hour", "day", "month"):
                spec = f"datetime:{granularity}"
                local = Model.with_context(tz="America/Mexico_City")
                observed[f"{spec} tz"] = _rows(local, [], [spec], ["value:sum"])
            observed["two granularities"] = _rows(
                Model, [], ["date:year", "date:month"], ["value:sum"]
            )
            return observed

        self._diff((Test_Read_GroupFill_Temporal,), script)

    def test_many2many_groupbys(self):
        def script(env):
            Tag = env["test_read_group.tag"]
            red, blue, gone = Tag.create(
                [{"name": "red"}, {"name": "blue"}, {"name": "gone", "active": False}]
            )
            User = env["test_read_group.user"]
            ann, bob = User.create([{"name": "ann"}, {"name": "bob"}])
            Task = env["test_read_group.task"]
            Task.create(
                [
                    {
                        "name": "t1",
                        "tag_ids": [(6, 0, [red.id, blue.id, gone.id])],
                        "user_ids": [(6, 0, [ann.id, bob.id])],
                        "integer": 1,
                    },
                    {
                        "name": "t2",
                        "tag_ids": [(6, 0, [blue.id])],
                        "user_ids": [(6, 0, [bob.id])],
                        "integer": 2,
                    },
                    {"name": "t3", "tag_ids": [(6, 0, [gone.id])], "integer": 4},
                    {"name": "t4", "integer": 8},
                ]
            )
            env.flush_all()
            env.invalidate_all()
            observed = {}
            for groupby in (
                ["tag_ids"],
                ["active_tag_ids"],
                ["all_tag_ids"],
                ["user_ids"],
                ["tag_ids", "user_ids"],
                ["user_ids", "integer"],
            ):
                observed[str(groupby)] = _rows(
                    Task, [], groupby, ["__count", "integer:sum", "name:array_agg"]
                )
                observed[f"{groupby} desc"] = _rows(
                    Task,
                    [],
                    groupby,
                    ["__count"],
                    order=", ".join([f"{groupby[0]} desc", *groupby[1:]]),
                )
            observed["count distinct"] = _rows(
                Task,
                [],
                [],
                ["tag_ids:count_distinct", "user_ids:count", "tag_ids:recordset"],
            )
            return observed

        self._diff(
            (Test_Read_GroupTask, Test_Read_GroupUser, Test_Read_GroupTag), script
        )

    def test_sum_currency_picks_the_latest_past_rate_per_company(self):
        def script(env):
            today = fields.Date.context_today(env["res.currency"])
            usd, eur = env["res.currency"].create(
                [{"name": "USX", "symbol": "$"}, {"name": "EUX", "symbol": "€"}]
            )
            company = env.company
            env["res.currency.rate"].search([]).unlink()
            env["res.currency.rate"].create(
                [
                    # eur: a shared past rate loses to the company's own future
                    # one, and the company's latest past rate wins over a later
                    # future one
                    {
                        "currency_id": eur.id,
                        "name": today - datetime.timedelta(days=30),
                        "rate": 0.5,
                    },
                    {
                        "currency_id": eur.id,
                        "name": today - datetime.timedelta(days=10),
                        "rate": 0.8,
                        "company_id": company.id,
                    },
                    {
                        "currency_id": eur.id,
                        "name": today - datetime.timedelta(days=1),
                        "rate": 0.9,
                        "company_id": company.id,
                    },
                    {
                        "currency_id": eur.id,
                        "name": today + datetime.timedelta(days=5),
                        "rate": 4.0,
                        "company_id": company.id,
                    },
                    # usd: only future rates, the earliest applies
                    {
                        "currency_id": usd.id,
                        "name": today + datetime.timedelta(days=9),
                        "rate": 2.0,
                    },
                    {
                        "currency_id": usd.id,
                        "name": today + datetime.timedelta(days=2),
                        "rate": 1.25,
                    },
                ]
            )
            Model = env["test_read_group.aggregate.monetary"]
            Model.create(
                [
                    {"name": "k1", "currency_id": eur.id, "total_in_currency_id": 9.0},
                    {"name": "k1", "currency_id": usd.id, "total_in_currency_id": 5.0},
                    {"name": "k2", "currency_id": usd.id, "total_in_currency_id": 2.5},
                    {"name": "k2", "total_in_currency_id": 3.0},
                ]
            )
            return {
                "all": _rows(Model, [], [], ["total_in_currency_id:sum_currency"]),
                "by name": _rows(
                    Model, [], ["name"], ["total_in_currency_id:sum_currency"]
                ),
            }

        observed = self._diff(
            (
                Test_Read_GroupAggregateMonetary,
                TestReadGroupAggregateMonetaryRelated,
                _StubCurrency,
                _StubCurrencyRate,
            ),
            script,
        )
        self.assertEqual(
            observed["all"], [(9.0 / 0.9 + 5.0 / 1.25 + 2.5 / 1.25 + 3.0,)]
        )


@tagged("post_install", "-at_install")
class TestReadGroupBackendWalk(TestReadGroupBackendMatrix):
    """The four scripts above are hand-written; this one is drawn. Random rows,
    then random `_read_group` calls over the groupbys, aggregates, orders,
    domains, havings, limits and offsets both tiers claim to answer, compared
    row for row. An emulation shortcut nobody wrote a case for fails here."""

    SCALAR_GROUPBYS = ([], ["key"], ["key", "partner_id"], ["partner_id"], ["value"])
    SCALAR_AGGREGATES = (
        ["__count"],
        ["value:sum"],
        ["value:sum", "value:max", "value:min"],
        ["numeric_value:avg"],
        ["value:count"],
        ["value:count_distinct"],
        ["key:array_agg"],
        ["value:sum", "__count"],
    )
    SCALAR_DOMAINS = (
        [],
        [("value", ">", 0)],
        [("key", "in", [1, 2])],
        [("partner_id", "!=", False)],
        [("numeric_value", "<", 0.5)],
    )
    TEMPORAL_GROUPBYS = (
        ["date:month"],
        ["date:year"],
        ["date:quarter"],
        ["date:week"],
        ["datetime:day"],
        ["datetime:hour"],
        ["datetime:month", "value"],
        ["date:month", "datetime:day"],
    )
    TEMPORAL_AGGREGATES = (["value:sum"], ["__count"], ["value:sum", "value:max"])
    TEMPORAL_DOMAINS = (
        [],
        [("date", ">=", "2026-02-01")],
        [("datetime", "<", "2026-01-16 00:00:00")],
        [("value", ">", 2)],
    )

    def _draw_plan(self, rng, calls, groupbys, aggregates, domains, having_terms):
        plan = []
        for _ in range(calls):
            groupby = rng.choice(groupbys)
            aggs = rng.choice(aggregates)
            order = None
            if rng.random() < 0.5 and (groupby or aggs):
                term = rng.choice([*groupby, *aggs])
                order = ", ".join(
                    [
                        f"{term}{rng.choice(['', ' desc'])}",
                        *(g for g in groupby if g != term),
                    ]
                )
            having = None
            for term, operators, values in having_terms:
                if term in aggs and rng.random() < 0.3:
                    having = [(term, rng.choice(operators), rng.choice(values))]
                    break
            limit = rng.choice([None, None, 2, 3])
            offset = rng.choice([0, 0, 1]) if limit else 0
            plan.append(
                (rng.choice(domains), groupby, aggs, order, having, limit, offset)
            )
        return plan

    @staticmethod
    def _observe(Model, plan):
        return {
            f"{index}: {domain} {groupby} {aggs} {order} {having} {limit} {offset}": (
                _rows(
                    Model,
                    domain,
                    groupby,
                    aggs,
                    order=order,
                    having=having,
                    limit=limit,
                    offset=offset,
                )
            )
            for index, (
                domain,
                groupby,
                aggs,
                order,
                having,
                limit,
                offset,
            ) in enumerate(plan)
        }

    HAVING = (
        ("__count", (">=", ">"), (1, 2, 3)),
        ("value:sum", ("<", ">"), (-3, 0, 6)),
    )

    def _scalar_script(self, seed):
        rng = random.Random(seed)
        rows = [
            {
                "key": rng.choice([0, 1, 2, 3]),
                "value": rng.randint(-5, 9),
                "numeric_value": round(rng.random(), 2),
                "partner": rng.choice([None, "zulu", "alpha", "alpha"]),
            }
            for _ in range(rng.randint(3, 14))
        ]
        plan = self._draw_plan(
            rng,
            25,
            self.SCALAR_GROUPBYS,
            self.SCALAR_AGGREGATES,
            self.SCALAR_DOMAINS,
            self.HAVING,
        )

        def script(env):
            partners = {
                name: env["res.partner"].create({"name": name})
                for name in ("zulu", "alpha")
            }
            Model = env["test_read_group.aggregate"]
            Model.create(
                [
                    {
                        "key": row["key"],
                        "value": row["value"],
                        "numeric_value": row["numeric_value"],
                        "partner_id": (
                            partners[row["partner"]].id if row["partner"] else False
                        ),
                    }
                    for row in rows
                ]
            )
            return self._observe(Model, plan)

        return script

    def _temporal_script(self, seed):
        rng = random.Random(seed)
        rows = [
            {
                "date": rng.choice(
                    [
                        False,
                        "2025-11-30",
                        "2026-01-15",
                        "2026-02-01",
                        "2026-02-28",
                        "2026-07-04",
                    ]
                ),
                "datetime": rng.choice(
                    [
                        False,
                        "2026-01-15 23:30:00",
                        "2026-01-16 03:00:00",
                        "2026-02-01 12:00:00",
                        "2026-02-01 12:45:00",
                    ]
                ),
                "value": rng.randint(-2, 9),
            }
            for _ in range(rng.randint(3, 12))
        ]
        plan = self._draw_plan(
            rng,
            20,
            self.TEMPORAL_GROUPBYS,
            self.TEMPORAL_AGGREGATES,
            self.TEMPORAL_DOMAINS,
            self.HAVING,
        )

        def script(env):
            Model = env["test_read_group.fill_temporal"]
            Model.create(rows)
            return self._observe(Model, plan)

        return script

    def _diff_seeds(self, classes, draw):
        # every seed starts from the rows the in-memory tier starts from: none
        for seed in range(12):
            with self.subTest(seed=seed), self.env.cr.savepoint() as savepoint:
                try:
                    self._diff(classes, draw(seed), msg=f"seed {seed}")
                finally:
                    self.env.invalidate_all()
                    savepoint.rollback()

    def _grouping_sets_script(self, seed):
        rng = random.Random(seed)
        rows = [
            {
                "key": rng.choice([0, 1, 2, 3]),
                "value": rng.randint(-5, 9),
                "numeric_value": round(rng.random(), 2),
                "partner": rng.choice([None, "zulu", "alpha", "alpha"]),
            }
            for _ in range(rng.randint(3, 12))
        ]
        plan = []
        for _ in range(15):
            sets = [rng.choice(self.SCALAR_GROUPBYS) for _ in range(rng.randint(1, 3))]
            aggs = rng.choice(self.SCALAR_AGGREGATES)
            order = None
            if any("partner_id" not in groupby for groupby in sets):
                # a many2one order term sorts the sets that lack it by
                # ANY_VALUE() of the joined name, which PostgreSQL picks
                # arbitrarily, while the in-memory tier drops the term for
                # those sets; and without it the sets that have it tie
                # arbitrarily. Neither is wrong, and no caller orders a set
                # by a column it does not group by: the many2one is drawn
                # only when every set groups by it
                sets = [[t for t in groupby if t != "partner_id"] for groupby in sets]
            terms = sorted({term for groupby in sets for term in groupby})
            if rng.random() < 0.5 and (terms or aggs):
                # the groupby terms break the ties an aggregate leaves; a
                # term a set lacks is dropped for that set
                term = rng.choice([*terms, *aggs])
                order = ", ".join(
                    [
                        f"{term}{rng.choice(['', ' desc'])}",
                        *(t for t in terms if t != term),
                    ]
                )
            plan.append((rng.choice(self.SCALAR_DOMAINS), sets, aggs, order))

        def script(env):
            partners = {
                name: env["res.partner"].create({"name": name})
                for name in ("zulu", "alpha")
            }
            Model = env["test_read_group.aggregate"]
            Model.create(
                [
                    {
                        "key": row["key"],
                        "value": row["value"],
                        "numeric_value": row["numeric_value"],
                        "partner_id": (
                            partners[row["partner"]].id if row["partner"] else False
                        ),
                    }
                    for row in rows
                ]
            )
            observed = {}
            for index, (domain, sets, aggs, order) in enumerate(plan):
                try:
                    result = Model._read_grouping_sets(domain, sets, aggs, order=order)
                except NotImplementedError:
                    result = NotImplemented
                except ValueError as error:
                    result = str(error)
                else:
                    result = [
                        [tuple(_spell(v) for v in row) for row in rows_of_set]
                        for rows_of_set in result
                    ]
                observed[f"{index}: {domain} {sets} {aggs} {order}"] = result
            return observed

        return script

    def test_drawn_scalar_read_groups_agree(self):
        self._diff_seeds((Test_Read_GroupAggregate, _StubPartner), self._scalar_script)

    def test_drawn_grouping_sets_agree(self):
        self._diff_seeds(
            (Test_Read_GroupAggregate, _StubPartner), self._grouping_sets_script
        )

    def test_drawn_temporal_read_groups_agree(self):
        self._diff_seeds((Test_Read_GroupFill_Temporal,), self._temporal_script)

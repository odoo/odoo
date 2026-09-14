import datetime
import itertools

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
# tiers compare: a record by its name (ids differ), a float exactly
def _spell(value):
    if hasattr(value, "_ids"):
        return tuple(sorted(value.mapped("display_name"), key=repr) if value else ())
    if isinstance(value, list):
        return sorted((_spell(v) for v in value), key=repr)
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
        self.assertEqual(
            obs_a,
            obs_b,
            f"in-memory read_group diverged from SQL{': ' + msg if msg else ''}",
        )
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

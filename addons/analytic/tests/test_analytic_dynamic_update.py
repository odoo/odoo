from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.analytic.tests.common import AnalyticCommon


@tagged('post_install', '-at_install')
class TestAnalyticDynamicUpdate(AnalyticCommon):
    def test_configurations(self):
        @contextmanager
        def capture_create():
            container = {'created': self.env['account.analytic.line']}
            super_create = self.env.registry['account.analytic.line'].create

            def patch_create(self, vals_list):
                records = super_create(self, vals_list)
                container['created'] += records
                return records

            with patch.object(self.env.registry['account.analytic.line'], 'create', patch_create):
                yield container

        plan2 = self.analytic_account_3.plan_id._column_name()
        plan1 = self.analytic_account_1.plan_id._column_name()
        for comment, init, update, expect in [(
            "Add a distribution on a previously empty plan",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 40},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 60},
            ], {
                '__update__': [plan2],
                f"{self.analytic_account_3.id}": 25,
                f"{self.analytic_account_4.id}": 75,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 10.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 15.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 30.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 45.0},
            ],
        ), (
            "Add a distribution on a previously empty plan, both less than 100%",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 20},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 30},
            ], {
                '__update__': [plan2],
                f"{self.analytic_account_3.id}": 10,
                f"{self.analytic_account_4.id}": 40,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 2.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 3.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 8.0},
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 10.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 12.0},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 15.0},
            ],
        ), (
            "Add a distribution on a previously empty plan, both more than 100%",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 200},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 300},
            ], {
                '__update__': [plan2],
                f"{self.analytic_account_3.id}": 100,
                f"{self.analytic_account_4.id}": 400,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 40.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 60.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 160.0},
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 160.0},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 640.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 240.0},
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 240.0},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 960.0},
            ],
        ), (
            "Update the percentage of one plan without changing the other",
            [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 10},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 15},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 30},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 45},
            ], {
                '__update__': [plan1, plan2],
                f"{self.analytic_account_1.id},{self.analytic_account_3.id}": 15,
                f"{self.analytic_account_2.id},{self.analytic_account_3.id}": 10,
                f"{self.analytic_account_1.id},{self.analytic_account_4.id}": 45,
                f"{self.analytic_account_2.id},{self.analytic_account_4.id}": 30,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 1.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 2.25},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 4.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 6.75},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 1.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 4.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 3.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 1.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 6.75},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 4.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 3.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 13.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 9.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 4.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 20.25},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 13.5},
            ],
        ), (
            "Update the percentage on both plans at the same time",
            [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 10},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 15},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 30},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 45},
            ], {
                '__update__': [plan1, plan2],
                f"{self.analytic_account_1.id},{self.analytic_account_3.id}": 45,
                f"{self.analytic_account_2.id},{self.analytic_account_3.id}": 30,
                f"{self.analytic_account_1.id},{self.analytic_account_4.id}": 15,
                f"{self.analytic_account_2.id},{self.analytic_account_4.id}": 10,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 4.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 6.75},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 13.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 20.25},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 3.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 1.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 1.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 4.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 2.25},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 1.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 9.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 4.5},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 3.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 13.5},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 6.75},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 4.5},
            ],
        ), (
            "Remove everything set on plan 1",
            [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 45},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 30},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 15},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 10},
            ], {
                '__update__': [plan1],
            }, [
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 45.0},
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 30.0},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 15.0},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 10.0},
            ],
        ), (
            "Nothing changes because there is nothing in __update__",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 40},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 60},
            ], {
                '__update__': [],
            }, [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 40.0},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 60.0},
            ],
        ), (
            "Add a distribution on a previously empty plan, with more than 100%",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 40},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 60},
            ], {
                '__update__': [plan2],
                f"{self.analytic_account_3.id}": 33,
                f"{self.analytic_account_4.id}": 167,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 6.6},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 9.9},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 33.4},
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 6.6},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 33.4},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 50.1},
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 9.9},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 50.1},
            ],
        ), (
            "Add a distribution on a previously empty plan, with previous values more than 100%",
            [
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 33},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 167},
            ], {
                '__update__': [plan1],
                f"{self.analytic_account_1.id}": 40,
                f"{self.analytic_account_2.id}": 60,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 13.2},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 66.8},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 19.8},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 100.2},
            ],
        ), (
            "Add a distribution on a previously empty plan, with less than 100%",
            [
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 40},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 60},
            ], {
                '__update__': [plan2],
                f"{self.analytic_account_3.id}": 20,
                f"{self.analytic_account_4.id}": 30,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 8.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 12.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 12.0},
                {plan1: self.analytic_account_1.id, plan2: False, 'amount': 20.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 18.0},
                {plan1: self.analytic_account_2.id, plan2: False, 'amount': 30.0},
            ],
        ), (
            "Add a distribution on a previously empty plan, with previous values less than 100%",
            [
                {plan1: False, plan2: self.analytic_account_3.id, 'amount': 20},
                {plan1: False, plan2: self.analytic_account_4.id, 'amount': 30},
            ], {
                '__update__': [plan1],
                f"{self.analytic_account_1.id}": 40,
                f"{self.analytic_account_2.id}": 60,
            }, [
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_3.id, 'amount': 8.0},
                {plan1: self.analytic_account_1.id, plan2: self.analytic_account_4.id, 'amount': 12.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_3.id, 'amount': 12.0},
                {plan1: self.analytic_account_2.id, plan2: self.analytic_account_4.id, 'amount': 18.0},
            ],
        )]:
            with self.subTest(comment=comment):
                lines = self.env['account.analytic.line'].create([
                    {'name': 'test'} | vals
                    for vals in init
                ])
                with capture_create() as container:
                    lines.analytic_distribution = update
                lines.invalidate_recordset(['analytic_distribution'])
                self.assertRecordValues(lines + container['created'], expect)

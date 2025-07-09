# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime

from odoo.addons.base.tests.common import BaseCommon
from odoo.tests import tagged

from freezegun import freeze_time


class TestOverviewGraph(BaseCommon):
    @freeze_time("2024-06-06 11:00")
    def test_date_category_utc(self):
        self.env.user.tz = "UTC"
        summaries = defaultdict(float)
        month_day_to_category = {
            3: "before",
            4: "before",
            5: "yesterday",
            6: "today",
            7: "day_1",
            8: "day_2",
            9: "after",
            10: "after",
        }
        datetime_list = [datetime(2024, 6, day, 14, 0) for day in month_day_to_category]
        summaries = self.env["stock.picking"].calculate_date_category(datetime_list, summaries)
        expected_results = {
            "total_before": 2.0,
            "total_yesterday": 1.0,
            "total_today": 1.0,
            "total_day_1": 1.0,
            "total_day_2": 1.0,
            "total_after": 2.0,
        }
        for key, value in expected_results.items():
            self.assertEqual(
                summaries[key],
                value,
                f"Wrong summary for {key}, expected {value} but got {summaries[key]}",
            )

    @freeze_time("2024-06-06 11:00")
    def test_date_category_utc_plus_2h(self):
        self.env.user.tz = "Europe/Brussels"
        datetime_to_category = {
            datetime(2024, 6, 5, 21, 0): "yesterday",
            datetime(2024, 6, 5, 23, 0): "today",
            datetime(2024, 6, 6, 10, 0): "today",
            datetime(2024, 6, 6, 21, 0): "today",
            datetime(2024, 6, 6, 23, 0): "day_1",
        }
        for dt, expected_category in datetime_to_category.items():
            category = self.env["stock.picking"].calculate_date_category([dt], defaultdict(float))
            self.assertTrue(category[f"total_{expected_category}"], f"Wrong category calculated for {dt}")

    @freeze_time("2024-06-06 11:00")
    def test_date_category_utc_minus_3h(self):
        self.env.user.tz = "America/Sao_Paulo"
        datetime_to_category = {
            datetime(2024, 6, 6, 2, 0): "yesterday",
            datetime(2024, 6, 6, 4, 0): "today",
            datetime(2024, 6, 6, 9, 0): "today",
            datetime(2024, 6, 7, 2, 0): "today",
            datetime(2024, 6, 7, 3, 0): "day_1",
        }

        for dt, expected_category in datetime_to_category.items():
            category = self.env["stock.picking"].calculate_date_category([dt], defaultdict(float))
            self.assertTrue(category[f"total_{expected_category}"], f"Wrong category calculated for {dt}")

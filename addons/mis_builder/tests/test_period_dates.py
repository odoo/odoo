# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common
from odoo import fields

from ..models.mis_report_instance import (
    MODE_FIX,
    MODE_NONE,
    MODE_REL,
    SRC_SUMCOL,
    DateFilterForbidden,
    DateFilterRequired,
)
from .common import assert_matrix


class TestPeriodDates(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.report_obj = self.env["mis.report"]
        self.instance_obj = self.env["mis.report.instance"]
        self.period_obj = self.env["mis.report.instance.period"]
        self.report = self.report_obj.create(dict(name="test-report"))
        self.instance = self.instance_obj.create(
            dict(name="test-instance", report_id=self.report.id, comparison_mode=False)
        )
        self.assertEqual(len(self.instance.period_ids), 1)
        self.period = self.instance.period_ids[0]

    def assertDateEqual(self, first, second, msg=None):
        self.assertEqual(first, fields.Date.from_string(second), msg)

    def test_date_filter_constraints(self):
        self.instance.comparison_mode = True
        with self.assertRaises(DateFilterRequired):
            self.period.write(dict(mode=MODE_NONE))
        with self.assertRaises(DateFilterForbidden):
            self.period.write(dict(mode=MODE_FIX, source=SRC_SUMCOL))

    def test_simple_mode(self):
        # not comparison_mode
        self.assertFalse(self.instance.comparison_mode)
        period = self.instance.period_ids[0]
        self.assertEqual(period.date_from, self.instance.date_from)
        self.assertEqual(period.date_to, self.instance.date_to)

    def tests_mode_none(self):
        self.instance.comparison_mode = True
        self.period.write(dict(mode=MODE_NONE, source=SRC_SUMCOL))
        self.assertFalse(self.period.date_from)
        self.assertFalse(self.period.date_to)
        self.assertTrue(self.period.valid)

    def tests_mode_fix(self):
        self.instance.comparison_mode = True
        self.period.write(
            dict(
                mode=MODE_FIX,
                manual_date_from="2017-01-01",
                manual_date_to="2017-12-31",
            )
        )
        self.assertDateEqual(self.period.date_from, "2017-01-01")
        self.assertDateEqual(self.period.date_to, "2017-12-31")
        self.assertTrue(self.period.valid)

    def test_rel_day(self):
        self.instance.write(dict(comparison_mode=True, date="2017-01-01"))
        self.period.write(dict(mode=MODE_REL, type="d", offset="-2"))
        self.assertDateEqual(self.period.date_from, "2016-12-30")
        self.assertDateEqual(self.period.date_to, "2016-12-30")
        self.assertTrue(self.period.valid)

    def test_rel_day_ytd(self):
        self.instance.write(dict(comparison_mode=True, date="2019-05-03"))
        self.period.write(dict(mode=MODE_REL, type="d", offset="-2", is_ytd=True))
        self.assertDateEqual(self.period.date_from, "2019-01-01")
        self.assertDateEqual(self.period.date_to, "2019-05-01")
        self.assertTrue(self.period.valid)

    def test_rel_week(self):
        self.instance.write(dict(comparison_mode=True, date="2016-12-30"))
        self.period.write(dict(mode=MODE_REL, type="w", offset="1", duration=2))
        # from Monday to Sunday, the week after 2016-12-30
        self.assertDateEqual(self.period.date_from, "2017-01-02")
        self.assertDateEqual(self.period.date_to, "2017-01-15")
        self.assertTrue(self.period.valid)

    def test_rel_week_ytd(self):
        self.instance.write(dict(comparison_mode=True, date="2019-05-27"))
        self.period.write(
            dict(mode=MODE_REL, type="w", offset="1", duration=2, is_ytd=True)
        )
        self.assertDateEqual(self.period.date_from, "2019-01-01")
        self.assertDateEqual(self.period.date_to, "2019-06-16")
        self.assertTrue(self.period.valid)

    def test_rel_month(self):
        self.instance.write(dict(comparison_mode=True, date="2017-01-05"))
        self.period.write(dict(mode=MODE_REL, type="m", offset="1"))
        self.assertDateEqual(self.period.date_from, "2017-02-01")
        self.assertDateEqual(self.period.date_to, "2017-02-28")
        self.assertTrue(self.period.valid)

    def test_rel_month_ytd(self):
        self.instance.write(dict(comparison_mode=True, date="2019-05-15"))
        self.period.write(dict(mode=MODE_REL, type="m", offset="-1", is_ytd=True))
        self.assertDateEqual(self.period.date_from, "2019-01-01")
        self.assertDateEqual(self.period.date_to, "2019-04-30")
        self.assertTrue(self.period.valid)

    def test_rel_year(self):
        self.instance.write(dict(comparison_mode=True, date="2017-05-06"))
        self.period.write(dict(mode=MODE_REL, type="y", offset="1"))
        self.assertDateEqual(self.period.date_from, "2018-01-01")
        self.assertDateEqual(self.period.date_to, "2018-12-31")
        self.assertTrue(self.period.valid)

    def test_rel_date_range(self):
        # create a few date ranges
        date_range_type = self.env["date.range.type"].create(dict(name="Year"))
        for year in (2016, 2017, 2018):
            self.env["date.range"].create(
                dict(
                    type_id=date_range_type.id,
                    name="%d" % year,
                    date_start="%d-01-01" % year,
                    date_end="%d-12-31" % year,
                    company_id=date_range_type.company_id.id,
                )
            )
        self.instance.write(dict(comparison_mode=True, date="2017-06-15"))
        self.period.write(
            dict(
                mode=MODE_REL,
                type="date_range",
                date_range_type_id=date_range_type.id,
                offset="-1",
                duration=3,
            )
        )
        self.assertDateEqual(self.period.date_from, "2016-01-01")
        self.assertDateEqual(self.period.date_to, "2018-12-31")
        self.assertTrue(self.period.valid)

    def test_dates_in_expr(self):
        self.env["mis.report.kpi"].create(
            dict(
                report_id=self.report.id,
                name="k1",
                description="kpi 1",
                expression="(date_to - date_from).days + 1",
            )
        )
        self.instance.date_from = "2017-01-01"
        self.instance.date_to = "2017-01-31"
        matrix = self.instance._compute_matrix()
        assert_matrix(matrix, [[31]])

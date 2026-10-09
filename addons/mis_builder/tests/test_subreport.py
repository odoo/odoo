# Copyright 2020 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

from odoo.addons.mis_builder.models.expression_evaluator import ExpressionEvaluator
from odoo.addons.mis_builder.models.mis_report_subreport import (
    InvalidNameError,
    ParentLoopError,
)


class TestMisSubreport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # create report
        cls.subreport = cls.env["mis.report"].create(dict(name="test subreport"))
        cls.subreport_kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.subreport.id,
                name="sk1",
                description="subreport kpi 1",
                expression="11",
            )
        )
        cls.report = cls.env["mis.report"].create(
            dict(
                name="test report",
                subreport_ids=[
                    (0, 0, dict(name="subreport", subreport_id=cls.subreport.id))
                ],
            )
        )
        cls.report_kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.report.id,
                name="k1",
                description="report kpi 1",
                expression="subreport.sk1 + 1",
            )
        )
        cls.parent_report = cls.env["mis.report"].create(
            dict(
                name="parent report",
                subreport_ids=[(0, 0, dict(name="report", subreport_id=cls.report.id))],
            )
        )
        cls.parent_report_kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=cls.parent_report.id,
                name="pk1",
                description="parent report kpi 1",
                expression="report.k1 + 1",
            )
        )

    def test_basic(self):
        ee = ExpressionEvaluator(aep=None, date_from="2017-01-01", date_to="2017-01-16")
        d = self.report._evaluate(ee)
        assert d["k1"] == 12

    def test_two_levels(self):
        ee = ExpressionEvaluator(aep=None, date_from="2017-01-01", date_to="2017-01-16")
        d = self.parent_report._evaluate(ee)
        assert d["pk1"] == 13

    def test_detect_loop(self):
        with self.assertRaises(ParentLoopError):
            self.report.write(
                dict(
                    subreport_ids=[
                        (
                            0,
                            0,
                            dict(name="preport1", subreport_id=self.parent_report.id),
                        )
                    ]
                )
            )
        with self.assertRaises(ParentLoopError):
            self.report.write(
                dict(
                    subreport_ids=[
                        (
                            0,
                            0,
                            dict(name="preport2", subreport_id=self.report.id),
                        )
                    ]
                )
            )

    def test_invalid_name(self):
        with self.assertRaises(InvalidNameError):
            self.report.subreport_ids[0].name = "ab c"

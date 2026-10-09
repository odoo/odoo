# Copyright 2017 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo_test_helper import FakeModelLoader

from odoo.tests.common import TransactionCase

from ..models.mis_kpi_data import ACC_AVG, ACC_SUM


class TestKpiData(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .fake_models import MisKpiDataTestItem

        cls.loader.update_registry((MisKpiDataTestItem,))

        report = cls.env["mis.report"].create(dict(name="test report"))
        cls.kpi1 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=report.id,
                name="k1",
                description="kpi 1",
                expression="AccountingNone",
            )
        )
        cls.expr1 = cls.kpi1.expression_ids[0]
        cls.kpi2 = cls.env["mis.report.kpi"].create(
            dict(
                report_id=report.id,
                name="k2",
                description="kpi 2",
                expression="AccountingNone",
            )
        )
        cls.expr2 = cls.kpi2.expression_ids[0]
        cls.kd11 = cls.env["mis.kpi.data.test.item"].create(
            dict(
                kpi_expression_id=cls.expr1.id,
                date_from="2017-05-01",
                date_to="2017-05-10",
                amount=10,
            )
        )
        cls.kd12 = cls.env["mis.kpi.data.test.item"].create(
            dict(
                kpi_expression_id=cls.expr1.id,
                date_from="2017-05-11",
                date_to="2017-05-20",
                amount=20,
            )
        )
        cls.kd13 = cls.env["mis.kpi.data.test.item"].create(
            dict(
                kpi_expression_id=cls.expr1.id,
                date_from="2017-05-21",
                date_to="2017-05-25",
                amount=30,
            )
        )
        cls.kd21 = cls.env["mis.kpi.data.test.item"].create(
            dict(
                kpi_expression_id=cls.expr2.id,
                date_from="2017-06-01",
                date_to="2017-06-30",
                amount=3,
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        return super().tearDownClass()

    def test_kpi_data_name(self):
        self.assertEqual(self.kd11.name, "k1: 2017-05-01 - 2017-05-10")
        self.assertEqual(self.kd12.name, "k1: 2017-05-11 - 2017-05-20")

    def test_kpi_data_sum(self):
        self.assertEqual(self.kpi1.accumulation_method, ACC_SUM)
        # one full
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-10", []
        )
        self.assertEqual(r, {self.expr1: 10})
        # one half
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-05", []
        )
        self.assertEqual(r, {self.expr1: 5})
        # two full
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-20", []
        )
        self.assertEqual(r, {self.expr1: 30})
        # two half
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-06", "2017-05-15", []
        )
        self.assertEqual(r, {self.expr1: 15})
        # more than covered range
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-01-01", "2017-05-31", []
        )
        self.assertEqual(r, {self.expr1: 60})
        # two kpis
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-21", "2017-06-30", []
        )
        self.assertEqual(r, {self.expr1: 30, self.expr2: 3})

    def test_kpi_data_avg(self):
        self.kpi1.accumulation_method = ACC_AVG
        # one full
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-10", []
        )
        self.assertEqual(r, {self.expr1: 10})
        # one half
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-05", []
        )
        self.assertEqual(r, {self.expr1: 10})
        # two full
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-01", "2017-05-20", []
        )
        self.assertEqual(r, {self.expr1: (10 * 10 + 20 * 10) / 20})
        # two half
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-05-06", "2017-05-15", []
        )
        self.assertEqual(r, {self.expr1: (10 * 5 + 20 * 5) / 10})
        # more than covered range
        r = self.env["mis.kpi.data.test.item"]._query_kpi_data(
            "2017-01-01", "2017-05-31", []
        )
        self.assertEqual(r, {self.expr1: (10 * 10 + 20 * 10 + 30 * 5) / 25})

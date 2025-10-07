# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import time
from datetime import date

import pytz
from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import common, tagged
from odoo.tools import test_reports

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCard(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create uom:
        uom_id = cls.env.ref("uom.product_uom_unit")

        # Create products:
        cls.product_A = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "uom_id": uom_id.id,
                "uom_po_id": uom_id.id,
            }
        )

        # Create location:
        cls.location_1 = cls.env.ref("stock.stock_location_stock")
        cls.location_2 = cls.env.ref("stock.stock_location_customers")

        # Create operation type:
        operation_type = cls.env.ref("stock.picking_type_in")

        # Create stock picking:
        picking = cls.env["stock.picking"].create(
            {
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
                "picking_type_id": operation_type.id,
            }
        )
        cls.env["stock.move"].create(
            {
                "name": cls.product_A.name,
                "product_id": cls.product_A.id,
                "product_uom_qty": 50.000,
                "product_uom": cls.product_A.uom_id.id,
                "picking_id": picking.id,
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
            }
        )
        picking.action_confirm()
        picking.move_ids_without_package.quantity_done = 50.000
        picking.button_validate()

        cls.model = cls._getReportModel(cls)

        cls.qweb_report_name = cls._getQwebReportName(cls)
        cls.xlsx_report_name = cls._getXlsxReportName(cls)
        cls.xlsx_action_name = cls._getXlsxReportActionName(cls)

        cls.report_title = cls._getReportTitle(cls)

        cls.base_filters = cls._getBaseFilters(cls)

        cls.report = cls.model.create(cls.base_filters)
        cls.report._compute_results()

    def test_html(self):
        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            self.qweb_report_name,
            [self.report.id],
            report_type="qweb-html",
        )

    def test_qweb(self):
        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            self.qweb_report_name,
            [self.report.id],
            report_type="qweb-pdf",
        )

    def test_xlsx(self):
        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            self.xlsx_report_name,
            [self.report.id],
            report_type="xlsx",
        )

    def test_print(self):
        self.report.print_report("qweb")
        self.report.print_report("xlsx")

    def _getReportModel(self):
        return self.env["report.stock.card.report"]

    def _getQwebReportName(self):
        return "stock_card_report.report_stock_card_report_pdf"

    def _getXlsxReportName(self):
        return "stock_card_report.report_stock_card_report_xlsx"

    def _getXlsxReportActionName(self):
        return "stock_card_report.action_report_stock_card_report_xlsx"

    def _getReportTitle(self):
        return "Stock Card Report"

    def _getBaseFilters(self):
        return {
            "product_ids": [Command.set([self.product_A.id])],
            "location_id": self.location_1.id,
        }


@freeze_time("2022-02-01 00:00:00")
@tagged("post_install", "-at_install")
class TestStockCardReport(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create uom:
        uom_id = cls.env.ref("uom.product_uom_unit")

        # Create products:
        cls.product_A = cls.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "uom_id": uom_id.id,
                "uom_po_id": uom_id.id,
            }
        )
        cls.product_B = cls.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "uom_id": uom_id.id,
                "uom_po_id": uom_id.id,
            }
        )

        # Create location:
        cls.location_1 = cls.env.ref("stock.stock_location_stock")
        cls.location_2 = cls.env.ref("stock.stock_location_customers")

        # Create operation type:
        operation_type = cls.env.ref("stock.picking_type_in")

        cls.datetime_now = fields.Datetime.now()

        # Create stock picking:
        cls.picking_1 = cls.env["stock.picking"].create(
            {
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
                "picking_type_id": operation_type.id,
            }
        )
        cls.env["stock.move"].create(
            {
                "name": cls.product_A.name,
                "product_id": cls.product_A.id,
                "product_uom_qty": 50.000,
                "product_uom": cls.product_A.uom_id.id,
                "picking_id": cls.picking_1.id,
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
            }
        )
        cls.picking_1.action_confirm()
        cls.picking_1.move_ids_without_package.quantity_done = 50.000
        cls.picking_1.button_validate()

        cls.picking_2 = cls.env["stock.picking"].create(
            {
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
                "picking_type_id": operation_type.id,
            }
        )
        cls.env["stock.move"].create(
            {
                "name": cls.product_B.name,
                "product_id": cls.product_B.id,
                "product_uom_qty": 100.000,
                "product_uom": cls.product_B.uom_id.id,
                "picking_id": cls.picking_2.id,
                "location_id": cls.location_2.id,
                "location_dest_id": cls.location_1.id,
            }
        )
        cls.picking_2.action_confirm()
        cls.picking_2.move_ids_without_package.quantity_done = 100.000
        cls.picking_2.button_validate()

    def test_reports(self):
        report = self.env["report.stock.card.report"].create(
            {
                "product_ids": [Command.set([self.product_A.id, self.product_B.id])],
                "location_id": self.location_1.id,
            }
        )
        report._compute_results()
        # Check the date in 'stock.move' because
        # standard odoo keep the datetime without timezone
        self.assertEqual(
            self.picking_1.move_ids_without_package.date, self.datetime_now
        )
        user_timezone = pytz.timezone(self.env.user.tz)
        picking_date_user_tz = self.picking_1.move_ids_without_package.date.astimezone(
            user_timezone
        ).replace(tzinfo=None)

        # Date in report should be in user timezone
        for res in report.results:
            self.assertEqual(res.date, picking_date_user_tz)

        report.print_report("qweb")
        report.print_report("xlsx")

    def test_get_report_html(self):
        report = self.env["report.stock.card.report"].create(
            {
                "product_ids": [Command.set([self.product_A.id, self.product_B.id])],
                "location_id": self.location_1.id,
            }
        )
        report._compute_results()
        report.get_html(given_context={"active_id": report.id})

    def test_wizard_date_range(self):
        date_range = self.env["date.range"]
        self.type = self.env["date.range.type"].create(
            {"name": "Month", "company_id": False, "allow_overlap": False}
        )
        dt = date_range.create(
            {
                "name": "FiscalYear",
                "date_start": time.strftime("%Y-%m-01"),
                "date_end": time.strftime("%Y-%m-28"),
                "type_id": self.type.id,
            }
        )
        wizard = self.env["stock.card.report.wizard"].create(
            {
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
                "product_ids": [Command.set([self.product_A.id, self.product_B.id])],
                "location_id": self.location_1.id,
            }
        )
        wizard._onchange_date_range_id()
        self.assertEqual(
            wizard.date_from, date(date.today().year, date.today().month, 1)
        )
        self.assertEqual(
            wizard.date_to, date(date.today().year, date.today().month, 28)
        )
        wizard._export("qweb-pdf")
        wizard.button_export_html()
        wizard.button_export_pdf()
        wizard.button_export_xlsx()

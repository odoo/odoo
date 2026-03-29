# Copyright  2018 Forest and Biomass Romania
# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import date

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestVATReport(AccountTestInvoicingCommon):
    @classmethod
    def init_invoice(
        cls,
        move_type,
        name=None,
        partner=None,
        invoice_date=None,
        post=False,
        lines=None,
        taxes=None,
    ):
        move_form = Form(
            cls.env["account.move"].with_context(default_move_type=move_type)
        )
        move_form.invoice_date = invoice_date or fields.Date.from_string("2019-01-01")
        move_form.partner_id = partner or cls.partner_a
        lines = lines or []
        for line in lines:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = line[0]
                line_form.name = "Test"
                line_form.account_id = line[1]
                line_form.quantity = line[2]
                line_form.price_unit = line[3]
                if taxes:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(taxes)
        rslt = move_form.save()
        if post:
            rslt.action_post()
        return rslt

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.date_from = time.strftime("%Y-%m-01")
        cls.date_to = time.strftime("%Y-%m-28")
        cls.company = cls.env.user.company_id
        cls.company.country_id = cls.env.ref("base.us").id
        cls.receivable_account = cls.company_data["default_account_receivable"]
        cls.income_account = cls.company_data["default_account_revenue"]
        cls.expense_account = cls.company_data["default_account_expense"]
        cls.tax_account = cls.env["account.account"].search(
            [
                ("company_ids", "in", [cls.company.id]),
                (
                    "account_type",
                    "=",
                    "liability_non_current",
                ),
            ],
            limit=1,
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.tax_tag_01 = cls.env["account.account.tag"].create(
            {
                "name": "Tag 01",
                "applicability": "taxes",
                "country_id": cls.company.country_id.id,
            }
        )
        cls.tax_tag_02 = cls.env["account.account.tag"].create(
            {
                "name": "Tag 02",
                "applicability": "taxes",
                "country_id": cls.company.country_id.id,
            }
        )
        cls.tax_tag_03 = cls.env["account.account.tag"].create(
            {
                "name": "Tag 03",
                "applicability": "taxes",
                "country_id": cls.company.country_id.id,
            }
        )
        cls.tax_group_10 = cls.env["account.tax.group"].create(
            {"name": "Tax 10%", "sequence": 1}
        )
        cls.tax_group_20 = cls.env["account.tax.group"].create(
            {"name": "Tax 20%", "sequence": 2}
        )
        cls.tax_10 = cls.env["account.tax"].create(
            {
                "name": "Tax 10.0%",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group_10.id,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.tax_account.id,
                            "tag_ids": [(6, 0, [cls.tax_tag_01.id, cls.tax_tag_02.id])],
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.tax_account.id,
                        },
                    ),
                ],
            }
        )
        cls.tax_20 = cls.env["account.tax"].create(
            {
                "sequence": 30,
                "name": "Tax 20.0%",
                "amount": 20.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": cls.company.id,
                "cash_basis_transition_account_id": cls.tax_account.id,
                "tax_group_id": cls.tax_group_20.id,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.tax_account.id,
                            "tag_ids": [(6, 0, [cls.tax_tag_02.id, cls.tax_tag_03.id])],
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.tax_account.id,
                        },
                    ),
                ],
            }
        )
        cls.init_invoice(
            "out_invoice",
            name="Test invoice 1",
            partner=cls.env.ref("base.res_partner_2"),
            invoice_date=time.strftime("%Y-%m-03"),
            post=True,
            lines=[
                (cls.env.ref("product.product_product_4"), cls.income_account, 1, 100.0)
            ],
            taxes=cls.tax_10,
        )
        cls.init_invoice(
            "out_invoice",
            name="Test invoice 2",
            partner=cls.env.ref("base.res_partner_2"),
            invoice_date=time.strftime("%Y-%m-04"),
            post=True,
            lines=[
                (
                    cls.env.ref("product.product_product_4"),
                    cls.income_account,
                    1,
                    250.0,
                ),
            ],
            taxes=cls.tax_20,
        )

    def _get_report_lines(self, taxgroups=False):
        based_on = "taxtags"
        if taxgroups:
            based_on = "taxgroups"
        vat_report = self.env["vat.report.wizard"].create(
            {
                "date_from": self.date_from,
                "date_to": self.date_to,
                "company_id": self.company.id,
                "based_on": based_on,
                "tax_detail": True,
            }
        )
        data = vat_report._prepare_vat_report()
        res_data = self.env[
            "report.account_financial_report.vat_report"
        ]._get_report_values(vat_report, data)
        return res_data

    def check_tag_or_group_in_report(self, tag_or_group_name, vat_report):
        tag_or_group_in_report = False
        for tag_or_group in vat_report:
            if tag_or_group["name"] == tag_or_group_name:
                tag_or_group_in_report = True
                break
        return tag_or_group_in_report

    def check_tax_in_report(self, tax_name, vat_report):
        tax_in_report = False
        for tag_or_group in vat_report:
            if tag_or_group["taxes"]:
                for tax in tag_or_group["taxes"]:
                    if tax["name"] == tax_name:
                        tax_in_report = True
        return tax_in_report

    def _get_tag_or_group_line(self, tag_or_group_name, vat_report):
        tag_or_group_net = False
        tag_or_group_tax = False
        for tag_or_group in vat_report:
            if tag_or_group["name"] == tag_or_group_name:
                tag_or_group_net = tag_or_group["net"]
                tag_or_group_tax = tag_or_group["tax"]
        return tag_or_group_net, tag_or_group_tax

    def _get_tax_line(self, tax_name, vat_report):
        tax_net = False
        tax_tax = False
        for tag_or_group in vat_report:
            if tag_or_group["taxes"]:
                for tax in tag_or_group["taxes"]:
                    if tax["name"] == tax_name:
                        tax_net = tax["net"]
                        tax_tax = tax["tax"]
        return tax_net, tax_tax

    def test_01_compute(self):
        # Generate the vat lines
        res_data = self._get_report_lines()
        vat_report = res_data["vat_report"]

        # Check report based on taxtags
        check_tax_tag_01 = self.check_tag_or_group_in_report(
            self.tax_tag_01.name, vat_report
        )
        self.assertTrue(check_tax_tag_01)
        check_tax_tag_02 = self.check_tag_or_group_in_report(
            self.tax_tag_02.name, vat_report
        )
        self.assertTrue(check_tax_tag_02)
        check_tax_tag_03 = self.check_tag_or_group_in_report(
            self.tax_tag_03.name, vat_report
        )
        self.assertTrue(check_tax_tag_03)
        check_tax_10 = self.check_tax_in_report(self.tax_10.name, vat_report)
        self.assertTrue(check_tax_10)
        check_tax_20 = self.check_tax_in_report(self.tax_20.name, vat_report)
        self.assertTrue(check_tax_20)

        tag_01_net, tag_01_tax = self._get_tag_or_group_line(
            self.tax_tag_01.name, vat_report
        )
        tag_02_net, tag_02_tax = self._get_tag_or_group_line(
            self.tax_tag_02.name, vat_report
        )
        tag_03_net, tag_03_tax = self._get_tag_or_group_line(
            self.tax_tag_03.name, vat_report
        )
        tax_10_net, tax_10_tax = self._get_tax_line(self.tax_10.name, vat_report)
        tax_20_net, tax_20_tax = self._get_tax_line(self.tax_20.name, vat_report)

        self.assertEqual(tag_01_net, -100)
        self.assertEqual(tag_01_tax, -10)
        self.assertEqual(tag_02_net, -350)
        self.assertEqual(tag_02_tax, -60)
        self.assertEqual(tag_03_net, -250)
        self.assertEqual(tag_03_tax, -50)
        self.assertEqual(tax_10_net, -100)
        self.assertEqual(tax_10_tax, -10)
        self.assertEqual(tax_20_net, -250)
        self.assertEqual(tax_20_tax, -50)

        # Check report based on taxgroups
        res_data = self._get_report_lines(taxgroups=True)
        vat_report = res_data["vat_report"]

        check_group_10 = self.check_tag_or_group_in_report(
            self.tax_group_10.name, vat_report
        )
        self.assertTrue(check_group_10)
        check_group_20 = self.check_tag_or_group_in_report(
            self.tax_group_20.name, vat_report
        )
        self.assertTrue(check_group_20)
        check_tax_10 = self.check_tax_in_report(self.tax_10.name, vat_report)
        self.assertTrue(check_tax_10)
        check_tax_20 = self.check_tax_in_report(self.tax_20.name, vat_report)
        self.assertTrue(check_tax_20)

        group_10_net, group_10_tax = self._get_tag_or_group_line(
            self.tax_group_10.name, vat_report
        )
        group_20_net, group_20_tax = self._get_tag_or_group_line(
            self.tax_group_20.name, vat_report
        )
        tax_10_net, tax_10_tax = self._get_tax_line(self.tax_10.name, vat_report)
        tax_20_net, tax_20_tax = self._get_tax_line(self.tax_20.name, vat_report)

        self.assertEqual(group_10_net, -100)
        self.assertEqual(group_10_tax, -10)
        self.assertEqual(group_20_net, -250)
        self.assertEqual(group_20_tax, -50)
        self.assertEqual(tax_10_net, -100)
        self.assertEqual(tax_10_tax, -10)
        self.assertEqual(tax_20_net, -250)
        self.assertEqual(tax_20_tax, -50)

    def test_wizard_date_range(self):
        vat_wizard = self.env["vat.report.wizard"]
        date_range = self.env["date.range"]
        self.type = self.env["date.range.type"].create(
            {"name": "Month", "company_id": False, "allow_overlap": False}
        )
        dt = date_range.create(
            {
                "name": "FS2016",
                "date_start": time.strftime("%Y-%m-01"),
                "date_end": time.strftime("%Y-%m-28"),
                "type_id": self.type.id,
            }
        )
        wizard = vat_wizard.create(
            {
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
                "tax_detail": True,
            }
        )
        wizard.onchange_date_range_id()
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
        wizard = vat_wizard.create(
            {
                "date_range_id": dt.id,
                "date_from": time.strftime("%Y-%m-28"),
                "date_to": time.strftime("%Y-%m-01"),
                "based_on": "taxgroups",
                "tax_detail": True,
            }
        )
        wizard.onchange_date_range_id()
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

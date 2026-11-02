# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests.common import TransactionCase


class TestThaiTaxReports(TransactionCase):
    """Basic tests for the Thai tax report wizard."""

    def _create_wizard(self, **overrides):
        vals = {
            "date_from": fields.Date.today(),
            "date_to": fields.Date.today(),
            "company_id": self.env.company.id,
            "report_type": "vat_sales",
        }
        vals.update(overrides)
        return self.env["thai.tax.report.wizard"].create(vals)

    def test_create_wizard_defaults(self):
        wizard = self._create_wizard()
        self.assertEqual(wizard.report_type, "vat_sales")
        self.assertEqual(wizard.company_id, self.env.company)
        self.assertTrue(wizard.date_from)
        self.assertTrue(wizard.date_to)

    def test_wizard_report_types(self):
        for report_type in (
            "vat_sales",
            "vat_purchase",
            "wht",
            "pnd3",
            "pnd53",
            "pnd54",
            "pnd50",
            "pnd51",
        ):
            wizard = self._create_wizard(report_type=report_type)
            self.assertEqual(wizard.report_type, report_type)

    def test_wizard_date_range(self):
        date_from = fields.Date.today().replace(month=1, day=1)
        date_to = fields.Date.today().replace(month=12, day=31)
        wizard = self._create_wizard(date_from=date_from, date_to=date_to)
        self.assertEqual(wizard.date_from, date_from)
        self.assertEqual(wizard.date_to, date_to)

    def test_wht_certificate_report_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_wht_certificate")
        self.assertEqual(report.model, "withholding.tax.cert")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd54_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd54_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def _create_wht_move(self, income_tax_form, code_prefix):
        """Create a posted move plus its account.withholding.move for a form."""
        wht_account = self.env["account.account"].create(
            {
                "code": "%s1" % code_prefix,
                "name": "WHT Payable %s Test" % income_tax_form,
                "account_type": "asset_current",
                "wht_account": True,
            }
        )
        base_account = self.env["account.account"].create(
            {
                "code": "%s2" % code_prefix,
                "name": "Base %s Test" % income_tax_form,
                "account_type": "expense",
            }
        )
        wht_tax = self.env["account.withholding.tax"].create(
            {
                "name": "WHT %s 3%%" % income_tax_form.upper(),
                "account_id": wht_account.id,
                "amount": 3.0,
                "income_tax_form": income_tax_form,
            }
        )
        partner = self.env["res.partner"].create(
            {"name": "%s Vendor" % income_tax_form.upper()}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Base",
                            "debit": 1000.0,
                            "account_id": base_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT",
                            "credit": 1000.0,
                            "account_id": wht_account.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return self.env["account.withholding.move"].create(
            {
                "move_id": move.id,
                "partner_id": partner.id,
                "amount_income": 1000.0,
                "amount_wht": 30.0,
                "wht_tax_id": wht_tax.id,
                "company_id": self.env.company.id,
            }
        )

    def _wht_register_values(self, model_name, wht_move):
        return (
            self.env[model_name]
            .with_context(
                date_from=fields.Date.today(),
                date_to=fields.Date.today(),
                company_id=self.env.company.id,
            )
            ._get_report_values(wht_move.ids)
        )

    def test_pnd53_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd53_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd3_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd3_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd53_register_gathers_pnd53_withholding(self):
        """Only withholding moves flagged PND53 are listed by the register."""
        wht_move = self._create_wht_move("pnd53", code_prefix="X9921")
        values = self._wht_register_values(
            "report.od19_thai_tax_reports.pnd53_register", wht_move
        )
        self.assertEqual(len(values["lines"]), 1)
        self.assertEqual(values["lines"][0]["partner_name"], "PND53 Vendor")
        self.assertAlmostEqual(values["total_base"], 1000.0)
        self.assertAlmostEqual(values["total_wht"], 30.0)

    def test_pnd3_register_gathers_pnd3_withholding(self):
        """Only withholding moves flagged PND3 (or PND3a) are listed."""
        wht_move = self._create_wht_move("pnd3", code_prefix="X9922")
        values = self._wht_register_values(
            "report.od19_thai_tax_reports.pnd3_register", wht_move
        )
        self.assertEqual(len(values["lines"]), 1)
        self.assertEqual(values["lines"][0]["partner_name"], "PND3 Vendor")
        self.assertAlmostEqual(values["total_base"], 1000.0)
        self.assertAlmostEqual(values["total_wht"], 30.0)

    def test_pnd54_register_gathers_pnd54_withholding(self):
        """Only withholding moves flagged PND54 are listed by the register."""
        wht_account = self.env["account.account"].create(
            {
                "code": "X991001",
                "name": "WHT Payable PND54 Test",
                "account_type": "asset_current",
                "wht_account": True,
            }
        )
        base_account = self.env["account.account"].create(
            {
                "code": "X991002",
                "name": "PND54 Base Test",
                "account_type": "expense",
            }
        )
        wht_tax = self.env["account.withholding.tax"].create(
            {
                "name": "WHT PND54 3%",
                "account_id": wht_account.id,
                "amount": 3.0,
                "income_tax_form": "pnd54",
            }
        )
        partner = self.env["res.partner"].create({"name": "PND54 Vendor"})
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Base",
                            "debit": 1000.0,
                            "account_id": base_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT",
                            "credit": 1000.0,
                            "account_id": wht_account.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        wht_move = self.env["account.withholding.move"].create(
            {
                "move_id": move.id,
                "partner_id": partner.id,
                "amount_income": 1000.0,
                "amount_wht": 30.0,
                "wht_tax_id": wht_tax.id,
                "company_id": self.env.company.id,
            }
        )
        values = (
            self.env["report.od19_thai_tax_reports.pnd54_register"]
            .with_context(
                date_from=fields.Date.today(),
                date_to=fields.Date.today(),
                company_id=self.env.company.id,
            )
            ._get_report_values(wht_move.ids)
        )
        self.assertEqual(len(values["lines"]), 1)
        self.assertEqual(values["lines"][0]["partner_name"], "PND54 Vendor")
        self.assertAlmostEqual(values["total_base"], 1000.0)
        self.assertAlmostEqual(values["total_wht"], 30.0)

    def test_wht_certificate_report_renders_cert_lines(self):
        """The certificate prints the amounts carried by the OCA cert lines."""
        partner = self.env["res.partner"].create({"name": "WHT Vendor Test"})
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": partner.id,
                "company_id": self.env.company.id,
                "date": fields.Date.today(),
                "income_tax_form": "pnd53",
                "wht_line": [
                    (
                        0,
                        0,
                        {
                            "wht_cert_income_type": "5",
                            "base": 1000.0,
                            "amount": 30.0,
                        },
                    )
                ],
            }
        )
        report = self.env.ref("od19_thai_tax_reports.action_wht_certificate")
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(report, cert.ids)
        rendered = html.decode()
        self.assertIn("หนังสือรับรองการหักภาษี", rendered)
        self.assertIn("1,000.00", rendered)
        self.assertIn("30.00", rendered)

    def _create_pl_move(self):
        """สร้างรายการกำไร/ขาดทุนที่ Post แล้ว สำหรับทดสอบ ภ.ง.ด.50/51"""
        income = self.env["account.account"].create(
            {
                "code": "X993001",
                "name": "Income PND50 Test",
                "account_type": "income",
            }
        )
        expense = self.env["account.account"].create(
            {
                "code": "X993002",
                "name": "Expense PND50 Test",
                "account_type": "expense",
            }
        )
        asset = self.env["account.account"].create(
            {
                "code": "X993003",
                "name": "Cash PND50 Test",
                "account_type": "asset_current",
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (0, 0, {"name": "Income", "credit": 5000.0, "account_id": income.id}),
                    (0, 0, {"name": "Expense", "debit": 2000.0, "account_id": expense.id}),
                    (0, 0, {"name": "Cash", "debit": 3000.0, "account_id": asset.id}),
                ],
            }
        )
        move.action_post()
        return income, expense

    def test_pnd50_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd50_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd51_register_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_pnd51_register")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_pnd50_register_computes_profit_and_tax(self):
        """ภ.ง.ด.50 สรุปกำไรสุทธิตามบัญชีและคำนวณภาษีในอัตรา 20%"""
        self._create_pl_move()
        values = (
            self.env["report.od19_thai_tax_reports.pnd50_register"]
            .with_context(
                date_from=fields.Date.today(),
                date_to=fields.Date.today(),
                company_id=self.env.company.id,
            )
            ._get_report_values([])
        )
        self.assertGreaterEqual(values["total_income"], 5000.0)
        self.assertGreaterEqual(values["total_expense"], 2000.0)
        self.assertAlmostEqual(
            values["net_profit"], values["total_income"] - values["total_expense"]
        )
        self.assertAlmostEqual(
            values["taxable_profit"],
            values["net_profit"] if values["net_profit"] > 0 else 0.0,
        )
        self.assertAlmostEqual(values["tax_amount"], values["taxable_profit"] * 0.20)
        self.assertIn("X993001", [line["code"] for line in values["income_lines"]])

    def test_pnd51_register_estimates_half_year(self):
        """ภ.ง.ด.51 ประมาณการกำไรทั้งปีและคำนวณภาษีครึ่งปี (50%)"""
        self._create_pl_move()
        values = (
            self.env["report.od19_thai_tax_reports.pnd51_register"]
            .with_context(
                date_from=fields.Date.today(),
                date_to=fields.Date.today(),
                company_id=self.env.company.id,
            )
            ._get_report_values([])
        )
        self.assertGreaterEqual(values["months"], 1)
        self.assertAlmostEqual(
            values["net_profit"], values["total_income"] - values["total_expense"]
        )
        expected_annual = values["net_profit"] * 12.0 / values["months"]
        self.assertAlmostEqual(values["estimated_annual_profit"], expected_annual)
        self.assertAlmostEqual(
            values["estimated_annual_tax"],
            values["taxable_annual_profit"] * 0.20,
        )
        self.assertAlmostEqual(
            values["half_year_payable"], values["estimated_annual_tax"] * 0.5
        )

    def test_register_reports_render(self):
        """ทุกรายงานใน wizard ต้อง render ได้จริง (กัน template/report_name ไม่ตรง)"""
        report_map = {
            "vat_sales": (
                "od19_thai_tax_reports.action_vat_sales_register",
                "สมุดรายการภาษีขาย",
            ),
            "vat_purchase": (
                "od19_thai_tax_reports.action_vat_purchase_register",
                "สมุดรายการภาษีซื้อ",
            ),
            "wht": (
                "od19_thai_tax_reports.action_wht_register",
                "สมุดภาษีหัก ณ ที่จ่าย",
            ),
            "pp36": (
                "od19_thai_tax_reports.action_pp36_register",
                "ภ.พ.36",
            ),
            "pnd54": (
                "od19_thai_tax_reports.action_pnd54_register",
                "ภ.ง.ด.54",
            ),
            "pnd3": (
                "od19_thai_tax_reports.action_pnd3_register",
                "ภ.ง.ด.3",
            ),
            "pnd53": (
                "od19_thai_tax_reports.action_pnd53_register",
                "ภ.ง.ด.53",
            ),
            "pnd50": (
                "od19_thai_tax_reports.action_pnd50_register",
                "ภ.ง.ด.50",
            ),
            "pnd51": (
                "od19_thai_tax_reports.action_pnd51_register",
                "ภ.ง.ด.51",
            ),
        }
        for report_type, (xmlid, needle) in report_map.items():
            with self.subTest(report_type=report_type):
                wizard = self._create_wizard(report_type=report_type)
                report = self.env.ref(xmlid)
                html, _report_type = (
                    self.env["ir.actions.report"]
                    .with_context(
                        date_from=wizard.date_from,
                        date_to=wizard.date_to,
                        company_id=wizard.company_id.id,
                    )
                    ._render_qweb_html(report, wizard.ids)
                )
                self.assertIn(needle, html.decode())

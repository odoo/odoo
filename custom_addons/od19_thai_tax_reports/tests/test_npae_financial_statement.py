# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the NPAE financial statement (งบการเงินตามแบบ NPAE).

Covered: the report action binding, the Statement of Financial Position
(assets / liabilities / equity, current vs non-current) and the Statement of
Profit or Loss, including the accounting equation (assets = liabilities +
equity + result of the period).
"""

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestNpaeFinancialStatement(TransactionCase):
    """Basic tests for the NPAE financial statement report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.cash_account = cls.env["account.account"].create(
            {
                "code": "X995001",
                "name": "Cash NPAE Test",
                "account_type": "asset_current",
            }
        )
        cls.capital_account = cls.env["account.account"].create(
            {
                "code": "X995002",
                "name": "Capital NPAE Test",
                "account_type": "equity",
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "code": "X995003",
                "name": "Income NPAE Test",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "code": "X995004",
                "name": "Expense NPAE Test",
                "account_type": "expense",
            }
        )
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (0, 0, {"name": "Cash", "debit": 13000.0, "account_id": cls.cash_account.id}),
                    (0, 0, {"name": "Capital", "credit": 10000.0, "account_id": cls.capital_account.id}),
                    (0, 0, {"name": "Income", "credit": 5000.0, "account_id": cls.income_account.id}),
                    (0, 0, {"name": "Expense", "debit": 2000.0, "account_id": cls.expense_account.id}),
                ],
            }
        )
        move.action_post()
        cls.move = move

    def _get_values(self, **context):
        ctx = {
            "date_from": fields.Date.today().replace(month=1, day=1),
            "date_to": fields.Date.today(),
            "company_id": self.company.id,
        }
        ctx.update(context)
        return (
            self.env["report.od19_thai_tax_reports.npae_financial_statement"]
            .with_context(**ctx)
            ._get_report_values([])
        )

    def _assert_line(self, lines, code, expected):
        """ตรวจว่าบัญชี ``code`` ปรากฏในรายงานด้วยยอด ``expected``"""
        amounts = {line["code"]: line["amount"] for line in lines}
        self.assertIn(code, amounts, "account %s not found in report lines" % code)
        self.assertAlmostEqual(amounts[code], expected, places=2)

    def test_npae_report_is_bound(self):
        report = self.env.ref("od19_thai_tax_reports.action_npae_financial_statement")
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_npae_computes_balanced_statement(self):
        """งบการเงินต้องจัดหมวดบัญชีถูกต้อง และสมการบัญชีต้องลงตัว

        ใช้ช่วงเวลาที่ครอบคลุมรายการทั้งหมด (ปี 1900–2999) เพื่อให้
        ผลการดำเนินงานทั้งหมดถูกนำมาคิดในงวดเดียว จึงทำให้สมการบัญชี
        (สินทรัพย์ = หนี้สิน + ส่วนของผู้ถือหุ้น + ผลการดำเนินงาน) ลงตัวพอดี
        โดยไม่ขึ้นกับข้อมูล demo ที่อาจมีอยู่ในฐานข้อมูลทดสอบ
        """
        values = self._get_values(
            date_from=fields.Date.to_date("1900-01-01"),
            date_to=fields.Date.to_date("2999-12-31"),
        )
        self._assert_line(values["assets_current"], "X995001", 13000.0)
        self._assert_line(values["equity_lines"], "X995002", 10000.0)
        self._assert_line(values["income_lines"], "X995003", 5000.0)
        self._assert_line(values["expense_lines"], "X995004", 2000.0)
        self.assertAlmostEqual(
            values["net_profit"], values["total_income"] - values["total_expense"]
        )
        self.assertAlmostEqual(
            values["total_equity_with_result"],
            values["total_equity"] + values["net_profit"],
        )
        self.assertAlmostEqual(values["balance_difference"], 0.0, places=2)

    def test_npae_report_renders(self):
        report = self.env.ref("od19_thai_tax_reports.action_npae_financial_statement")
        wizard = self.env["thai.tax.report.wizard"].create(
            {
                "report_type": "npae",
                "date_from": fields.Date.today().replace(month=1, day=1),
                "date_to": fields.Date.today(),
                "company_id": self.company.id,
            }
        )
        html, _report_type = (
            self.env["ir.actions.report"]
            .with_context(
                date_from=wizard.date_from,
                date_to=wizard.date_to,
                company_id=wizard.company_id.id,
            )
            ._render_qweb_html(report, wizard.ids)
        )
        rendered = html.decode()
        self.assertIn("งบแสดงฐานะการเงิน", rendered)
        self.assertIn("งบกำไรขาดทุน", rendered)
        self.assertIn("13,000.00", rendered)

    def test_npae_wizard_prints(self):
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "npae",
                    "date_from": fields.Date.today().replace(month=1, day=1),
                    "date_to": fields.Date.today(),
                    "company_id": self.company.id,
                }
            )
        )
        action = wizard.action_print()
        self.assertEqual(
            action["report_name"], "od19_thai_tax_reports.npae_financial_statement"
        )

# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the ส.บช.3 financial statement filed with the DBD.

Covered: the report action binding, the reuse of the TFRS for NPAEs
totals, the DBD specific header data (registration number, tax id and the
150-day filing deadline) and the printable form.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

REPORT_XMLID = "od19_thai_tax_reports.action_sbc3_register"
REPORT_NAME = "od19_thai_tax_reports.sbc3_register"
NPAE_MODEL = "report.od19_thai_tax_reports.npae_financial_statement"


@tagged("post_install", "-at_install")
class TestSbc3Register(TransactionCase):
    """Basic tests for the ส.บช.3 (DBD) financial statement report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.company_registry = "0105558000014"
        cls.cash_account = cls.env["account.account"].create(
            {
                "code": "X996001",
                "name": "Cash SBC3 Test",
                "account_type": "asset_current",
            }
        )
        cls.capital_account = cls.env["account.account"].create(
            {
                "code": "X996002",
                "name": "Capital SBC3 Test",
                "account_type": "equity",
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "code": "X996003",
                "name": "Income SBC3 Test",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "code": "X996004",
                "name": "Expense SBC3 Test",
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

    def _get_values(self, **context):
        ctx = {
            "date_from": fields.Date.today().replace(month=1, day=1),
            "date_to": fields.Date.today(),
            "company_id": self.company.id,
        }
        ctx.update(context)
        return (
            self.env["report.od19_thai_tax_reports.sbc3_register"]
            .with_context(**ctx)
            ._get_report_values([])
        )

    def _create_wizard(self):
        return (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "sbc3",
                    "date_from": fields.Date.today().replace(month=1, day=1),
                    "date_to": fields.Date.today(),
                    "company_id": self.company.id,
                }
            )
        )

    def test_sbc3_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    def test_sbc3_reuses_npae_totals(self):
        """ยอดในฟอร์ม ส.บช.3 ต้องตรงกับงบการเงิน TFRS for NPAEs"""
        ctx = {
            "date_from": fields.Date.today().replace(month=1, day=1),
            "date_to": fields.Date.today(),
            "company_id": self.company.id,
        }
        npae = (
            self.env[NPAE_MODEL]
            .with_context(**ctx)
            ._get_report_values([])
        )
        sbc3 = self._get_values()
        for key in (
            "total_assets",
            "total_liabilities",
            "total_equity_with_result",
            "total_income",
            "total_expense",
            "net_profit",
            "balance_difference",
        ):
            self.assertAlmostEqual(sbc3[key], npae[key], places=2)

    def test_sbc3_header_carries_dbd_data(self):
        """ฟอร์มต้องมีเลขทะเบียนนิติบุคคลและกำหนดยื่น 150 วัน"""
        values = self._get_values()
        self.assertEqual(values["company_registration"], "0105558000014")
        self.assertEqual(values["retention_years"], 5)
        expected_deadline = fields.Date.today() + timedelta(days=150)
        self.assertEqual(values["filing_deadline"], expected_deadline)

    def test_sbc3_report_renders(self):
        report = self.env.ref(REPORT_XMLID)
        wizard = self._create_wizard()
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
        self.assertIn("ส.บช.3", rendered)
        self.assertIn("งบแสดงฐานะการเงิน", rendered)
        self.assertIn("งบกำไรขาดทุน", rendered)
        self.assertIn("0105558000014", rendered)
        self.assertIn("13,000.00", rendered)

    def test_sbc3_wizard_prints(self):
        wizard = self._create_wizard()
        action = wizard.action_print()
        self.assertEqual(action["report_name"], REPORT_NAME)

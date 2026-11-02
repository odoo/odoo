# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the ภ.ธ.40 Specific Business Tax (SBT) register.

Covered: the SBT tax configuration (3% + 0.3% local), the report action
binding, the listing of SBT taxed customer invoices, the exclusion of
regular invoices and the printable form.
"""

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

REPORT_XMLID = "od19_thai_tax_reports.action_sbt_pp40_register"
REPORT_NAME = "od19_thai_tax_reports.sbt_pp40_register"
SBT_MODEL = "report.od19_thai_tax_reports.sbt_pp40_register"
SBT_TAX_XMLID = "od19_thai_tax_reports.tax_sbt_specific"
SBT_LOCAL_TAX_XMLID = "od19_thai_tax_reports.tax_sbt_local"
SBT_TAX_GROUP_XMLID = "od19_thai_tax_reports.tax_group_sbt"


@tagged("post_install", "-at_install")
class TestSbtPp40Register(TransactionCase):
    """Basic tests for the ภ.ธ.40 (SBT) report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.sbt_tax = cls.env.ref(SBT_TAX_XMLID)
        cls.sbt_local_tax = cls.env.ref(SBT_LOCAL_TAX_XMLID)
        cls.tax_group = cls.env.ref(SBT_TAX_GROUP_XMLID)

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "SBT Test Buyer",
                "company_type": "company",
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "code": "X997001",
                "name": "Income SBT Test",
                "account_type": "income",
            }
        )
        cls._seq = 0

    def _create_invoice(self, amount=100000.0, taxes=None, invoice_date="2026-03-15"):
        self.__class__._seq += 1
        if taxes is None:
            taxes = [self.sbt_tax.id, self.sbt_local_tax.id]
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string(invoice_date),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SBT taxed revenue %03d" % self.__class__._seq,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.income_account.id,
                            "tax_ids": [(6, 0, taxes)],
                        },
                    )
                ],
            }
        )

    def _get_values(self, **context):
        ctx = {
            "date_from": "2026-03-01",
            "date_to": "2026-03-31",
            "company_id": self.company.id,
        }
        ctx.update(context)
        return (
            self.env[SBT_MODEL]
            .with_context(**ctx)
            ._get_report_values([])
        )

    # ------------------------------------------------------------------
    # Tax configuration
    # ------------------------------------------------------------------
    def test_sbt_tax_configuration(self):
        self.assertEqual(self.sbt_tax.amount, 3.0)
        self.assertEqual(self.sbt_local_tax.amount, 0.3)
        self.assertEqual(self.sbt_tax.type_tax_use, "sale")
        self.assertEqual(self.sbt_local_tax.type_tax_use, "sale")
        self.assertEqual(self.sbt_tax.tax_group_id, self.tax_group)
        self.assertEqual(self.sbt_local_tax.tax_group_id, self.tax_group)

    def test_sbt_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    # ------------------------------------------------------------------
    # Register content
    # ------------------------------------------------------------------
    def test_sbt_report_lists_taxed_invoices(self):
        invoice = self._create_invoice(amount=100000.0)
        invoice.action_post()

        values = self._get_values()
        row = next(
            (line for line in values["lines"] if line["name"] == invoice.name), None
        )
        self.assertTrue(row, "The SBT invoice must appear in the PP40 report")
        self.assertAlmostEqual(row["tax_base"], 100000.0, 2)
        self.assertAlmostEqual(row["sbt_amount"], 3000.0, 2)
        self.assertAlmostEqual(row["local_amount"], 300.0, 2)
        self.assertAlmostEqual(row["total_amount"], 3300.0, 2)
        self.assertGreaterEqual(values["total_sbt_amount"], 3000.0)
        self.assertGreaterEqual(values["total_amount"], 3300.0)

    def test_sbt_report_ignores_regular_invoices(self):
        vat_tax = self.env["account.tax"].create(
            {
                "name": "Test Standard Output VAT 7%",
                "amount_type": "percent",
                "amount": 7.0,
                "type_tax_use": "sale",
                "company_id": self.company.id,
            }
        )
        invoice = self._create_invoice(amount=5000.0, taxes=[vat_tax.id])
        invoice.action_post()

        values = self._get_values()
        names = [line["name"] for line in values["lines"]]
        self.assertNotIn(invoice.name, names)

    def test_sbt_report_nets_credit_notes(self):
        invoice = self._create_invoice(amount=100000.0)
        invoice.action_post()

        self.__class__._seq += 1
        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string("2026-03-20"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SBT credit note",
                            "quantity": 1.0,
                            "price_unit": 40000.0,
                            "account_id": self.income_account.id,
                            "tax_ids": [
                                (6, 0, [self.sbt_tax.id, self.sbt_local_tax.id])
                            ],
                        },
                    )
                ],
            }
        )
        refund.action_post()

        values = self._get_values()
        refund_row = next(
            (line for line in values["lines"] if line["name"] == refund.name), None
        )
        self.assertTrue(refund_row, "The credit note must appear in the PP40 report")
        # ใบลดหนี้แสดงเป็นค่าลบเพื่อหักกลบกับรายรับ
        self.assertAlmostEqual(refund_row["tax_base"], -40000.0, 2)
        self.assertAlmostEqual(refund_row["sbt_amount"], -1200.0, 2)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def test_sbt_report_renders(self):
        invoice = self._create_invoice(amount=100000.0)
        invoice.action_post()

        report = self.env.ref(REPORT_XMLID)
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "sbt_pp40",
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "company_id": self.company.id,
                }
            )
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
        self.assertIn("ภ.ธ.40", rendered)
        self.assertIn("ภาษีธุรกิจเฉพาะ", rendered)
        self.assertIn("100,000.00", rendered)
        self.assertIn("3,000.00", rendered)

    def test_sbt_wizard_prints(self):
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "sbt_pp40",
                    "date_from": "2026-03-01",
                    "date_to": "2026-03-31",
                    "company_id": self.company.id,
                }
            )
        )
        action = wizard.action_print()
        self.assertEqual(action["report_name"], REPORT_NAME)

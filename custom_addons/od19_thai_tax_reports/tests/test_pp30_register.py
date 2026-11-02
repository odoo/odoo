# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the ภ.พ.30 (PP30) VAT return register.

Covered: the report action binding, the reconciliation of output VAT
(ภาษีขาย) against deductible input VAT (ภาษีซื้อ), the exclusion of the
non-deductible input VAT (ภาษีซื้อต้องห้าม, Section 82/5) and the
printable form.
"""

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

REPORT_XMLID = "od19_thai_tax_reports.action_pp30_register"
REPORT_NAME = "od19_thai_tax_reports.pp30_register"
PP30_MODEL = "report.od19_thai_tax_reports.pp30_register"


@tagged("post_install", "-at_install")
class TestPp30Register(TransactionCase):
    """Basic tests for the ภ.พ.30 (VAT return) report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "PP30 Test Partner",
                "company_type": "company",
            }
        )
        cls.sale_tax = cls.env["account.tax"].create(
            {
                "name": "Test Output VAT 7% (PP30)",
                "amount_type": "percent",
                "amount": 7.0,
                "type_tax_use": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.purchase_tax = cls.env["account.tax"].create(
            {
                "name": "Test Input VAT 7% (PP30)",
                "amount_type": "percent",
                "amount": 7.0,
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
            }
        )
        cls.non_deductible_tax = cls.env.ref(
            "od19_thai_tax_reports.tax_input_vat_non_deductible"
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "code": "X996001",
                "name": "Income PP30 Test",
                "account_type": "income",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "code": "X996002",
                "name": "Expense PP30 Test",
                "account_type": "expense",
            }
        )
        cls._seq = 0

    def _create_move(self, move_type, amount, taxes, invoice_date="2026-04-15"):
        self.__class__._seq += 1
        if move_type in ("out_invoice", "out_refund"):
            account = self.income_account
        else:
            account = self.expense_account
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string(invoice_date),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "PP30 test line %03d" % self.__class__._seq,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": account.id,
                            "tax_ids": [(6, 0, [tax.id for tax in taxes])],
                        },
                    )
                ],
            }
        )

    def _post(self, move):
        # Vendor bills require a tax invoice number/date (l10n_th_account_tax).
        if (
            move.move_type in ("in_invoice", "in_refund")
            and "tax_invoice_ids" in move._fields
        ):
            self.__class__._seq += 1
            move.tax_invoice_ids.write(
                {
                    "tax_invoice_number": "PP30-TI-%03d" % self.__class__._seq,
                    "tax_invoice_date": move.invoice_date or fields.Date.today(),
                }
            )
        move.action_post()
        return move

    def _get_values(self, **context):
        ctx = {
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "company_id": self.company.id,
        }
        ctx.update(context)
        return self.env[PP30_MODEL].with_context(**ctx)._get_report_values([])

    # ------------------------------------------------------------------
    # Report binding
    # ------------------------------------------------------------------
    def test_pp30_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "thai.tax.report.wizard")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    # ------------------------------------------------------------------
    # Reconciliation of output VAT against input VAT
    # ------------------------------------------------------------------
    def test_pp30_reconciles_output_and_input_vat(self):
        invoice = self._create_move("out_invoice", 100000.0, [self.sale_tax])
        self._post(invoice)
        bill = self._create_move("in_invoice", 40000.0, [self.purchase_tax])
        self._post(bill)

        values = self._get_values()
        self.assertAlmostEqual(values["output_vat"], 7000.0, 2)
        self.assertAlmostEqual(values["input_vat"], 2800.0, 2)
        self.assertAlmostEqual(values["non_deductible_vat"], 0.0, 2)
        self.assertAlmostEqual(values["sales_base"], 100000.0, 2)
        self.assertAlmostEqual(values["purchase_base"], 40000.0, 2)
        # 7000 - 2800 = 4200 payable
        self.assertAlmostEqual(values["net_vat"], 4200.0, 2)
        self.assertAlmostEqual(values["vat_payable"], 4200.0, 2)
        self.assertAlmostEqual(values["vat_overpaid"], 0.0, 2)

    def test_pp30_reports_overpaid_when_input_exceeds_output(self):
        invoice = self._create_move("out_invoice", 10000.0, [self.sale_tax])
        self._post(invoice)
        bill = self._create_move("in_invoice", 50000.0, [self.purchase_tax])
        self._post(bill)

        values = self._get_values()
        # 700 - 3500 = -2800 -> overpaid (ยกไปเครดิตเดือนถัดไป)
        self.assertAlmostEqual(values["net_vat"], -2800.0, 2)
        self.assertAlmostEqual(values["vat_payable"], 0.0, 2)
        self.assertAlmostEqual(values["vat_overpaid"], 2800.0, 2)

    # ------------------------------------------------------------------
    # Section 82/5 - non-deductible input VAT is not claimable
    # ------------------------------------------------------------------
    def test_pp30_excludes_non_deductible_input_vat(self):
        invoice = self._create_move("out_invoice", 100000.0, [self.sale_tax])
        self._post(invoice)
        bill = self._create_move(
            "in_invoice", 40000.0, [self.purchase_tax, self.non_deductible_tax]
        )
        self._post(bill)

        values = self._get_values()
        # Only the deductible VAT (40000 * 7% = 2800) may be claimed.
        self.assertAlmostEqual(values["input_vat"], 2800.0, 2)
        # The non-deductible VAT (40000 * 7% = 2800) is shown separately.
        self.assertAlmostEqual(values["non_deductible_vat"], 2800.0, 2)
        self.assertAlmostEqual(values["net_vat"], 4200.0, 2)

    # ------------------------------------------------------------------
    # Netting of credit notes
    # ------------------------------------------------------------------
    def test_pp30_nets_credit_notes(self):
        invoice = self._create_move("out_invoice", 100000.0, [self.sale_tax])
        self._post(invoice)
        credit_note = self._create_move(
            "out_refund", 40000.0, [self.sale_tax], invoice_date="2026-04-20"
        )
        self._post(credit_note)

        values = self._get_values()
        # 7000 - 2800 = 4200 output VAT, no purchases
        self.assertAlmostEqual(values["output_vat"], 4200.0, 2)
        self.assertAlmostEqual(values["sales_base"], 60000.0, 2)
        self.assertAlmostEqual(values["net_vat"], 4200.0, 2)

    def test_pp30_ignores_moves_without_vat(self):
        move = self._create_move("out_invoice", 5000.0, [])
        self._post(move)

        values = self._get_values()
        names = [line["name"] for line in values["sales_lines"]]
        self.assertNotIn(move.name, names)
        self.assertAlmostEqual(values["output_vat"], 0.0, 2)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def test_pp30_report_renders(self):
        invoice = self._create_move("out_invoice", 100000.0, [self.sale_tax])
        self._post(invoice)

        report = self.env.ref(REPORT_XMLID)
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "pp30",
                    "date_from": "2026-04-01",
                    "date_to": "2026-04-30",
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
        self.assertIn("ภ.พ.30", rendered)
        self.assertIn("ภาษีขาย", rendered)
        self.assertIn("ภาษีซื้อ", rendered)
        self.assertIn("100,000.00", rendered)
        self.assertIn("7,000.00", rendered)

    def test_pp30_wizard_prints(self):
        wizard = (
            self.env["thai.tax.report.wizard"]
            .with_context(discard_logo_check=True)
            .create(
                {
                    "report_type": "pp30",
                    "date_from": "2026-04-01",
                    "date_to": "2026-04-30",
                    "company_id": self.company.id,
                }
            )
        )
        action = wizard.action_print()
        self.assertEqual(action["report_name"], REPORT_NAME)

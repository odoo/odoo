# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBrPix(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="br"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "123456789012345678",
                "partner_id": cls.company_data["company"].partner_id.id,
                "proxy_type": "br_random",
                "proxy_value": "71d6c6e1-64ea-4a11-9560-a10870c40ca2",
                "include_reference": True,
            }
        )

        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_a.id,
                "partner_bank_id": cls.partner_bank.id,
                "invoice_line_ids": [
                    Command.create({"quantity": 1, "price_unit": 12.30})
                ],  # .30 to make sure we keep the trailing zero
            }
        )

    def test_constraints(self):
        self.partner_bank.write({"proxy_type": "email", "proxy_value": "a@example.com"})
        with self.assertRaises(ValidationError, msg="not a valid email"):
            self.partner_bank.proxy_value = "example.com"

        self.partner_bank.write({"proxy_type": "br_cpf_cnpj", "proxy_value": "00740886967"})
        with self.assertRaises(ValidationError, msg="not a valid CPF"):
            self.partner_bank.proxy_value = "444444321"

        self.partner_bank.write({"proxy_type": "mobile", "proxy_value": "+5561912345678"})
        with self.assertRaises(ValidationError, msg="The mobile number"):
            self.partner_bank.proxy_value = "061912345678"

        self.partner_bank.write({"proxy_type": "br_random", "proxy_value": "71d6c6e1-64ea-4a11-9560-a10870c40ca2"})
        with self.assertRaises(ValidationError, msg="The random key"):
            self.partner_bank.proxy_value = "not a random key"

    def _get_qr_code_string(self):
        self.invoice.qr_code_method = "emv_qr"
        demo_payment_reference = "NFe TÉST 0001"  # É and spaces should be removed

        emv_qr_vals = self.invoice.partner_bank_id._get_qr_vals(
            qr_method=self.invoice.qr_code_method,
            amount=self.invoice.amount_residual,
            currency=self.invoice.currency_id,
            debtor_partner=self.invoice.partner_id,
            free_communication=demo_payment_reference,
            structured_communication=None,
        )

        return "".join(emv_qr_vals)

    def test_get_qr_vals(self):
        self.assertEqual(
            self._get_qr_code_string(),
            "00020101021226580014br.gov.bcb.pix013671d6c6e1-64ea-4a11-9560-a10870c40ca2520400005303986540512.305802BR5914COMPANY_1_DATA62150511NFeTEST000163044CCF",
        )

    def test_get_qr_vals_without_reference(self):
        self.partner_bank.include_reference = False
        self.assertEqual(
            self._get_qr_code_string(),
            "00020101021226580014br.gov.bcb.pix013671d6c6e1-64ea-4a11-9560-a10870c40ca2520400005303986540512.305802BR5914COMPANY_1_DATA62070503***6304B27F",
        )

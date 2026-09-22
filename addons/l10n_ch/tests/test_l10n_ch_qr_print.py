import logging

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("post_install_l10n", "post_install", "-at_install")
class QRPrintTest(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ch")
    def setUpClass(cls):
        super().setUpClass()
        # the partner must be located in Switzerland.
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Bobby",
                "country_id": cls.env.ref("base.ch").id,
            }
        )
        # The bank account must be QR-compatible
        cls.qr_bank_account = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "CH4431999123000889012",
                "partner_id": cls.env.company.partner_id.id,
                # The account is the company's own, printed on an outbound
                # invoice for the customer to pay into. account's
                # `_check_post_invoices` refuses to post an inbound invoice
                # carrying one that has not been verified, and
                # `allow_out_payment` is the flag Odoo overloads for "this
                # account has been confirmed as ours". Omitting it does not
                # test the QR builder, it asserts that guard does not exist.
                "allow_out_payment": True,
            }
        )
        cls.correct_invoice_chf = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "bank_account_id": cls.qr_bank_account.id,
                "currency_id": cls.env.ref("base.CHF").id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [(0, 0, {"product_id": cls.product_a.id})],
            }
        )

        cls.correct_invoice_eur = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "bank_account_id": cls.qr_bank_account.id,
                "currency_id": cls.env.ref("base.EUR").id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [(0, 0, {"product_id": cls.product_a.id})],
            }
        )

        cls.wrong_partner_invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_a.id,
                "bank_account_id": cls.qr_bank_account.id,
                "currency_id": cls.env.ref("base.EUR").id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [(0, 0, {"product_id": cls.product_a.id})],
            }
        )

    def print_qr_bill(self, invoice):
        try:
            invoice.action_invoice_sent()
            return True
        except UserError as e:
            _logger.warning(str(e))
            return False

    def test_print_qr(self):
        self.correct_invoice_chf.action_post()
        self.assertTrue(self.print_qr_bill(self.correct_invoice_chf))

        # The QR can also be printed if the currency is EUR
        self.env.ref("base.EUR").active = True
        self.correct_invoice_eur.action_post()
        self.assertTrue(self.print_qr_bill(self.correct_invoice_eur))

        # A normal invoice will be printed if the partner is not from Switzerland
        self.wrong_partner_invoice.action_post()
        self.assertTrue(self.print_qr_bill(self.wrong_partner_invoice))

        # However, a qr bill can't be printed with those infos
        self.assertFalse(self.wrong_partner_invoice.l10n_ch_is_qr_valid)

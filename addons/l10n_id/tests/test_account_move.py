from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):
    """ Test the transaction code (kode transaksi) on invoices and credit notes """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.l10n_id_kode_transaksi = '04'

    def test_kode_transaksi_from_partner(self):
        invoice = self._create_invoice(partner_id=self.partner_a)
        self.assertEqual(invoice.l10n_id_kode_transaksi, '04')

    def test_kode_transaksi_credit_note_from_reversed_invoice(self):
        """ A credit note takes the code of the invoice it reverses, not the partner's default. """
        invoice = self._create_invoice(partner_id=self.partner_a, l10n_id_kode_transaksi='02', post=True)
        credit_note = invoice._reverse_moves()
        self.assertEqual(credit_note.l10n_id_kode_transaksi, '02')

    def test_need_kode_transaksi(self):
        """ The code is only required on customer invoices and credit notes that have taxes. """
        taxed_invoice = self._create_invoice(partner_id=self.partner_a, invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000, tax_ids=self.tax_sale_a),
        ])
        untaxed_invoice = self._create_invoice(partner_id=self.partner_a, invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000, tax_ids=False),
        ])
        taxed_credit_note = self._create_invoice(move_type='out_refund', partner_id=self.partner_a, invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000, tax_ids=self.tax_sale_a),
        ])
        taxed_bill = self._create_invoice(move_type='in_invoice', partner_id=self.partner_a, invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000, tax_ids=self.tax_purchase_a),
        ])
        self.assertTrue(taxed_invoice.l10n_id_need_kode_transaksi)
        self.assertFalse(untaxed_invoice.l10n_id_need_kode_transaksi)
        self.assertTrue(taxed_credit_note.l10n_id_need_kode_transaksi)
        self.assertFalse(taxed_bill.l10n_id_need_kode_transaksi)

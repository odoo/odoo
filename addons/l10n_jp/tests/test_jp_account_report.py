# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPAccountReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.partner_a.lang = 'ja_JP'
        cls.env.ref('base.JPY').active = True
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jis_standard')

    def test_invoice_report_uses_jp_honorific_and_currency_header(self):
        invoice = self._create_invoice_one_line(
            move_type='out_invoice',
            partner_id=self.partner_a,
            currency_id=self.env.ref('base.JPY'),
            product_id=self.product_a,
            tax_ids=self.tax_sale_a,
            post=True,
        )
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)
        self.assertIn('Unit Price (円)', text)
        self.assertIn('Amount (円)', text)
        self.assertIn('対象額', text)

    def test_payment_receipt_uses_jp_honorific(self):
        payment = self.init_payment(100.0, partner=self.partner_a, post=True)

        html = self.env['ir.actions.report'].sudo()._render_qweb_html('account.report_payment_receipt', payment.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)

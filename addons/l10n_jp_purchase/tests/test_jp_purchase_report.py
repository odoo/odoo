# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPPurchaseReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.other_currency = cls.setup_other_currency('JPY')
        cls.partner_a.lang = 'ja_JP'
        cls.other_currency.active = True
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jis_standard')

    def test_purchase_order_report_uses_honorific_and_currency_header(self):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_qty': 1.0,
                'price_unit': 100.0,
                'date_planned': '2026-08-21',
                'tax_ids': False,
            })],
        })
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('purchase.report_purchaseorder', purchase_order.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)
        self.assertIn('Unit Price (円)', text)
        self.assertIn('Amount (円)', text)

    def test_purchase_quotation_report_uses_honorific(self):
        quotation = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_qty': 1.0,
                'price_unit': 100.0,
                'date_planned': '2026-08-21',
                'tax_ids': False,
            })],
        })
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('purchase.report_purchasequotation', quotation.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)

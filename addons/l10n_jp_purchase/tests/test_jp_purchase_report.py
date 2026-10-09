# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPPurchaseReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.env.ref('base.JPY').with_context(lang='ja_JP').currency_unit_label = '円'
        cls.partner_a.lang = 'ja_JP'
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')

    def test_currency_header_follows_the_vendor_language(self):
        order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id, 'price_unit': 100.0})],
        })
        html = self.env['ir.actions.report']._render_qweb_html('purchase.report_purchaseorder', order.ids)[0]
        text = html2plaintext(html)

        self.assertIn('(円)', text)

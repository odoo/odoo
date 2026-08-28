# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPSaleReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.partner_a.lang = 'ja_JP'
        cls.jpy_currency = cls.env.ref('base.JPY')
        cls.jpy_currency.active = True
        cls.jpy_pricelist = cls.env['product.pricelist'].create({
            'name': 'JPY Pricelist',
            'currency_id': cls.jpy_currency.id,
        })
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jis_standard')

    def test_sale_report_uses_honorific_and_currency_header(self):
        sale_order = self._create_sale_order_one_line(
            partner_id=self.partner_a,
            pricelist_id=self.jpy_pricelist.id,
            product_id=self.product_a,
            price_unit=100.0,
            tax_ids=self.tax_sale_a,
        )

        html = self.env['ir.actions.report'].sudo()._render_qweb_html('sale.report_saleorder', sale_order.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)
        self.assertIn('Unit Price (円)', text)
        self.assertIn('Amount (円)', text)

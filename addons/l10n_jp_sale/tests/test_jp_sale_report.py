# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPSaleReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
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
        # l10n_din5008_sale rewrites the surcharged unit price to the monetary
        # widget for every company rather than for its own layout. These tests
        # are about what the JP rule decides, not about which module ends up
        # styling the cell.
        cls.env['ir.ui.view'].search([('key', '=', 'l10n_din5008_sale.report_saleorder_document')]).active = False

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

    def _render_unit_prices(self, prices):
        """Render an order of (price_unit, discount) pairs and return its text."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'pricelist_id': self.jpy_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'price_unit': price_unit,
                    'discount': discount,
                })
                for price_unit, discount in prices
            ],
        })
        html = self.env['ir.actions.report'].sudo()._render_qweb_html('sale.report_saleorder', order.ids)[0]
        return html2plaintext(html)

    def test_unit_price_column_drops_a_decimal_part_worth_nothing(self):
        text = self._render_unit_prices([(202.0, 0.0), (105.0, 0.0)])

        self.assertNotIn('202.00', text)
        self.assertNotIn('105.00', text)

    def test_unit_price_column_follows_the_surcharged_price(self):
        # A negative discount prints the surcharged price, 200 + 10% = 220, and
        # that whole number is what lets the column go without its decimals.
        self.assertNotIn('220.00', self._render_unit_prices([(200.0, -10.0)]))

        # 101 + 10% = 111.10 keeps the decimals of the surcharge above it.
        text = self._render_unit_prices([(200.0, -10.0), (101.0, -10.0)])
        self.assertIn('220.00', text)
        self.assertIn('111.10', text)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml.html

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPSaleReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')

    def test_unit_price_column_drops_its_decimals_beside_a_whole_surcharge(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'price_unit': 200.0, 'discount': -10.0}),
                Command.create({'product_id': self.product_a.id, 'price_unit': 300.0}),
            ],
        })
        html = self.env['ir.actions.report']._render_qweb_html('sale.report_saleorder', order.ids)[0]

        self.assertEqual(self._get_unit_price_cells(html), ['220', '300'])

    def test_unit_price_column_keeps_its_decimals_beside_a_surcharge_that_needs_them(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'price_unit': 200.0, 'discount': -10.0}),
                Command.create({'product_id': self.product_a.id, 'price_unit': 105.0, 'discount': -3.0}),
                Command.create({'product_id': self.product_a.id, 'price_unit': 300.0}),
            ],
        })
        html = self.env['ir.actions.report']._render_qweb_html('sale.report_saleorder', order.ids)[0]

        self.assertEqual(self._get_unit_price_cells(html), ['220.00', '108.15', '300.00'])

    def _get_unit_price_cells(self, html):
        return [cell.text_content().strip() for cell in lxml.html.fromstring(html).xpath("//td[@name='td_product_priceunit']")]

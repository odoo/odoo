# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDin5008SaleReport(SaleCommon):

    def test_unit_price_currency(self):
        """ Every unit price of the order report shows the currency, the one of
        a line with a negative discount too. """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({'product_id': self.product.id, 'price_unit': 33.53}),
                Command.create({'product_id': self.service_product.id, 'price_unit': 10.0, 'discount': -10}),
            ],
        })
        report_html = self.env['ir.actions.report']._render_qweb_html('sale.action_report_saleorder', order.ids)[0]
        unit_prices = [
            ' '.join(cell.text_content().split())
            for cell in html.fromstring(report_html).xpath("//td[@name='td_product_priceunit']")
        ]
        self.assertEqual(len(unit_prices), 2)
        for unit_price, amount in zip(unit_prices, ('33.53', '11.00')):
            self.assertIn(order.currency_id.symbol, unit_price)
            self.assertIn(amount, unit_price)

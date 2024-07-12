# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command

@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPoSSaleL10NBe(TestPointOfSaleHttpCommon):

    @classmethod
    @TestPointOfSaleHttpCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()

    def test_settle_order_is_invoice(self):

        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
            'is_storable': True,
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 10,
                'tax_id': False,
            })],
        })

        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_pos_tour('PosSettleOrderIsInvoice', login="accountman")

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_lot_valuation import TestLotValuation


class TestLotValuationPurchase(TestLotValuation):
    def test_poline_price_unit(self):
        """ Purchase order line price unit is the average of the lots from the product form """
        partner = self.env['res.partner'].create({
            'name': 'partner'
        })
        self.product1.categ_id.property_cost_method = 'fifo'
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product1.id,
                    'product_qty': 10,
                    'product_uom_id': self.product1.uom_id.id,
                }),
            ],
        })
        self.assertEqual(po.order_line[0].price_unit, 6.0)

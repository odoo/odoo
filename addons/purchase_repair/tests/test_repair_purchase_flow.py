# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestRepairPurchaseFlow(PurchaseTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_repair_with_purchase_mto_link(self):
        """
        Test the integration between a repair order and a purchase order (MTO)
        for a product with 'Make to Order' (MTO) and 'Buy' routes.

        Validates that a repair order triggers a purchase order with correct product
        and quantity, and ensures proper linking via the procurement group.
        """
        self.route_mto.active = True
        rule = self.route_mto.rule_ids.filtered(lambda r: r.picking_type_id.code == 'repair_operation')
        rule.update({'procure_method': 'make_to_order'})

        seller = self.env['res.partner'].create({
            'name': 'Vendor',
        })

        product = self.product
        product.write({
            'route_ids': [Command.set([self.route_mto.id, self.route_buy.id])],
            'seller_ids': [
                Command.create({
                    'partner_id': seller.id,
                    'min_qty': 1,
                    'price': 150,
                }),
            ],
        })

        repair = self.env['repair.order'].create([
            {
                'move_ids': [
                    Command.create({
                        'repair_line_type': 'add',
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                    })
                ]
            }
        ])

        repair.action_validate()

        purchase = repair.move_ids.created_purchase_line_ids.order_id
        self.assertEqual(purchase.order_line.product_id, product)
        self.assertEqual(purchase.order_line.product_qty, 1.0)
        self.assertEqual(purchase.order_line.move_dest_ids.repair_id, repair)
        self.assertEqual(repair.purchase_count, 1)
        self.assertEqual(purchase.repair_count, 1)
        purchase.button_confirm()
        self.assertEqual(repair.purchase_count, 1)
        self.assertEqual(purchase.repair_count, 1)

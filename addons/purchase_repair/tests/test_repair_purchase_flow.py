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

    def test_repair_smart_buttons_with_purchase_mtso_link(self):
        """Check the link between repair and purchase orders when the repair
        parts are replenished in MTSO buy."""
        self.route_mto.active = True
        self.warehouse.repair_mto_pull_id.procure_method = 'mts_else_mto'
        self.product.write({
            'route_ids': [Command.set(self.route_mto.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'price': 150,
            })],
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        repair = self.env['repair.order'].create({
            'move_ids': [Command.create({
                'repair_line_type': 'add',
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
            })],
        })
        repair.action_repair_start()
        purchase = repair.reference_ids.purchase_ids
        self.assertRecordValues(purchase.order_line, [{
            'product_id': self.product.id,
            'product_qty': 1.0,
        }])
        self.assertEqual(repair.purchase_count, 1)
        self.assertEqual(purchase.repair_count, 1)
        self.assertEqual(repair.action_view_purchase_orders()['res_id'], purchase.id)
        self.assertEqual(purchase.action_view_repair_orders()['res_id'], repair.id)

    def test_repair_purchase_count_with_grouped_rfq(self):
        """Check that each repair finds the grouped PO replenishing its parts."""
        self.route_mto.active = True
        self.warehouse.repair_mto_pull_id.procure_method = 'make_to_order'
        self.vendor.group_rfq = 'all'
        self.product.write({
            'route_ids': [Command.set(self.route_mto.ids)],
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'price': 150,
            })],
        })
        repairs = self.env['repair.order'].create([{
            'move_ids': [Command.create({
                'repair_line_type': 'add',
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
            })],
        } for _ in range(2)])
        repairs.action_repair_start()

        purchase = repairs.move_ids.created_purchase_line_ids.order_id
        self.assertEqual(len(purchase), 1, "A single purchase order fulfills the entire demand.")
        self.assertEqual(purchase.order_line.move_dest_ids, repairs.move_ids)
        self.assertRecordValues(repairs, [
            {'purchase_count': 1},
            {'purchase_count': 1},
        ])
        self.assertEqual(purchase.repair_count, 2)

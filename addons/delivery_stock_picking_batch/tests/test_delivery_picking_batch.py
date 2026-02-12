# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestDeliveryPickingBatch(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type_out = cls.env.ref('stock.picking_type_out')
        cls.local_delivery_carrier = cls.env['delivery.carrier'].create({
            'name': 'Local Delivery - Testing',
            'fixed_price': 5.0,
            'free_over': True,
            'amount': 50,
            'sequence': 4,
            'delivery_type': 'fixed',
            'product_id': cls.env['product.product'].create({
                'name': 'Local Delivery - Testing',
                'default_code': 'Delivery_Testing',
                'type': 'service',
                'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
                'sale_ok': False,
                'purchase_ok': False,
                'list_price': 10.0,
                'invoice_policy': 'order'
            }).id
        })
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.package_type = cls.env['stock.package.type'].create({
            'name': 'normal package',
            'base_weight': 1.0,
        })

        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'is_storable': True,
            'weight': 1.0,
        })

    def test_batch_picking_pack_shipping_weight_compute(self):
        """ Having a batch transfer with 2+ of the same product across multiple pickings and adding
        the products to the same pack should result in an accurate computed shipping weight.gau
        """
        picking_create_vals = {
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.local_delivery_carrier.id,
        }

        batch = self.env['stock.picking.batch'].create({
            'picking_ids': [Command.create(picking_create_vals) for _ in range(2)],
        })

        for picking in batch.picking_ids:
            picking.move_ids = self.env['stock.move'].create({
                'product_id': self.product_a.id,
                'product_uom_qty': 1.0,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
            })
            picking.move_ids[0].quantity = 1.0

        pack_wizard_vals = batch.action_put_in_pack()
        pack_wizard = self.env[(pack_wizard_vals.get('res_model'))].with_context(pack_wizard_vals.get('context')).create({})
        pack_wizard.package_type_id = self.package_type.id
        self.assertEqual(pack_wizard.shipping_weight, 3.0)
        package = pack_wizard.action_put_in_pack()
        batch.action_done()
        self.assertEqual(package.weight, 3.0)

    def test_auto_batch_carrier_change_after_confirmation(self):
        """
            Test an auto batch scenario where pickings correctly join the correct batches when carrier is set after confirmation.
            The pickings looks like this:
            - picking_1: confirmed with carrier_1
            - picking_2: confirmed without carrier > carrier_1 is set after confirmation
            - picking_3: confirmed with carrier_2
            - picking_4: confirmed with carrier_1 > carrier_2 is set after confirmation
            The expected result is:
            - batch_1: picking_1, picking_2
            - batch_2: picking_3, picking_4
        """
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Delivery with Auto Batch',
            'sequence_code': 'TEST',
            'code': 'outgoing',
            'company_id': self.env.company.id,
            'warehouse_id': warehouse.id,
            'auto_batch': True,
            'batch_group_by_carrier': True,
        })

        carrier_1 = self.env['delivery.carrier'].create({
            'name': 'Carrier 1',
            'delivery_type': 'fixed',
            'fixed_price': 10.0,
            'product_id': self.env['product.product'].create({
                'name': 'Delivery Carrier 1',
                'type': 'service',
                'categ_id': self.env.ref('delivery.product_category_deliveries').id,
                'list_price': 10.0,
            }).id
        })
        carrier_2 = self.env['delivery.carrier'].create({
            'name': 'Carrier 2',
            'delivery_type': 'fixed',
            'fixed_price': 15.0,
            'product_id': self.env['product.product'].create({
                'name': 'Delivery Carrier 2',
                'type': 'service',
                'categ_id': self.env.ref('delivery.product_category_deliveries').id,
                'list_price': 15.0,
            }).id
        })

        self.env['stock.quant']._update_available_quantity(self.product_a, self.stock_location, 40)

        picking_1 = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': carrier_1.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_1.action_confirm()

        self.assertTrue(picking_1.batch_id, "Picking 1 should be in a batch")

        picking_2 = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': picking_2.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_2.action_confirm()

        # simulating setting carrier after confirming SO without setting a carrier
        picking_2.write({'carrier_id': carrier_1.id})

        self.assertEqual(picking_2.batch_id, picking_1.batch_id,
                        "Picking 2 should join the same batch as picking 1 (carrier 1)")

        picking_3 = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': carrier_2.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': picking_3.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_3.action_confirm()

        self.assertTrue(picking_3.batch_id, "Picking 3 should be in a batch")
        self.assertNotEqual(picking_3.batch_id, picking_1.batch_id,
                           "Picking 3 should be in a different batch than picking 1 and 2 (carrier 2)")

        # Test changing carrier on an confirmed SO but not batched yet
        picking_4 = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': carrier_1.id,
        })
        self.env['stock.move'].create({
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.product_a.uom_id.id,
            'picking_id': picking_4.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_4.action_confirm()
        picking_4.write({'carrier_id': carrier_2.id})

        self.assertTrue(picking_4.batch_id, "Picking 4 should be in a batch")
        self.assertEqual(picking_4.batch_id, picking_3.batch_id,
                           "Picking 4 should be in the same batch as picking 3")

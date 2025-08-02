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

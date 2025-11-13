from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpQuant(TestMrpCommon):

    def test_kit_product_reservation_flow(self):
        """Test that kit products are not cleaned"""

        product_kit = self.env['product.product'].create({
            'name': 'This product will be a kit',
            'type': 'consu',
            'is_storable': True
        })

        delivery = self.env['stock.picking'].create({
            'location_id': self.shelf_1.id,
            'location_dest_id': self.warehouse_1.lot_stock_id.id,
            'picking_type_id': self.picking_type_out.id,
            'move_line_ids': [Command.create({
                'product_id': product_kit.id,
                'quantity_product_uom': 1,
                'location_dest_id': self.warehouse_1.lot_stock_id.id,
            })]
        })

        delivery.action_confirm()
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_kit.product_tmpl_id.id,
            'product_id': product_kit.id,
            'product_qty': 1,
            'type': 'phantom',  # type kit
        })

        # Force recomputation of is_kits, since it's currently not recomputed automatically when BOM is created
        product_kit._compute_is_kits()
        delivery.move_ids.quantity = 1
        product_normal = self.env['product.product'].create({
            'name': 'Normal Product Test',
            'type': 'consu',
            'is_storable': True
        })

        # Should work without error
        product_normal.action_open_quants()

        # Ensure it's raise an error if we try to update quantity of kit product directly
        with self.assertRaises(UserError, msg="You should update the components quantity instead of directly updating the quantity of the kit product."):
            self.env['stock.quant']._update_available_quantity(
                product_kit,
                self.warehouse_1.lot_stock_id,
                10,
            )

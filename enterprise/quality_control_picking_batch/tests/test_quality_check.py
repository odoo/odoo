# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import tagged

from odoo.addons.quality_control.tests.test_common import TestQualityCommon


@tagged('post_install', '-at_install')
class TestQualityPickingBatch(TestQualityCommon):

    def test_wave_transfers_quality_check(self):

        """Test that quality checks are cleaned/reassigned/created when a lated wave transfer is created."""

        # Create a Quality Point per operation/product/quantity for incoming shipment.
        products = self.product | self.product_2 | self.product_3 | self.product_4
        control_types = ('operation', 'product', 'move_line')
        self.env['quality.point'].create([
            {
                'product_ids': [Command.set(product.ids)],
                'picking_type_ids': [Command.set([self.picking_type_id])],
                'measure_on': control_type,
            } for product, control_type in zip(products[:-1], control_types)
        ])
        # Create 2 incoming shipments
        receipts = self.env['stock.picking'].create([
            {
                'picking_type_id': self.picking_type_id,
                'partner_id': self.partner_id,
                'location_id': self.location_id,
                'location_dest_id': self.location_dest_id,
                'move_ids': [
                    Command.create({
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom_qty': 5,
                        'product_uom': product.uom_id.id,
                        'location_id': self.location_id,
                        'location_dest_id': self.location_dest_id
                    }) for product in products
                ]
            } for _ in range(2)
        ])
        # Confirm the receipt which should assign them and create the related checks.
        receipts.action_confirm()
        self.assertEqual(len(receipts.check_ids), 6)

        # Add an extra quantity on the second receipt to be able to split moves in 2 during the wave transfer
        receipts[1].move_ids.quantity = 6
        # An extra check should have been created for the control per move_line
        self.assertEqual(len(receipts.check_ids), 7)

        # Batch the lines of receipt 1 and the non-extra lines of receipt 2
        lines_to_batch = receipts.move_line_ids.filtered(lambda ml: ml.product_id != products[-1])[:6]
        lines_to_batch._add_to_wave()
        pickings = receipts | lines_to_batch.picking_id
        # There should be 2 new pickings
        self.assertEqual(len(pickings), 4)

        def _check_counts(pickings):
            # Returns picking ids with their counts of checks measured on 'operation', 'product', 'move_line'
            counts = []
            for picking in pickings:
                checks_per_type = picking.check_ids.grouped('measure_on')
                count = (picking.id, [len(checks_per_type.get('operation', [])), len(checks_per_type.get('product', [])), len(checks_per_type.get('move_line', []))])
                counts.append(count)
            return counts

        self.assertEqual(_check_counts(pickings), [
            (pickings[0].id, [0, 0, 0]),
            (pickings[1].id, [1, 1, 1]),
            (pickings[2].id, [1, 1, 1]),
            (pickings[3].id, [1, 1, 1]),
        ])

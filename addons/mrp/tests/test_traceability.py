# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon
import uuid

class TestTraceability(TestMrpCommon):
    TRACKING_TYPES = ['none', 'serial', 'lot']

    def _create_product(self, tracking):
        return self.env['product.product'].create({
            'name': 'Product %s' % tracking,
            'type': 'product',
            'tracking': tracking,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_tracking_types_on_mo(self):
        finished_no_track = self._create_product('none')
        finished_lot = self._create_product('lot')
        finished_serial = self._create_product('serial')
        consumed_no_track = self._create_product('none')
        consumed_lot = self._create_product('lot')
        consumed_serial = self._create_product('serial')
        stock_id = self.env.ref('stock.stock_location_stock').id
        inventory_adjustment = self.env['stock.inventory'].create({
            'name': 'Initial Inventory',
            'location_id': stock_id,
            'filter': 'partial',
        })
        inventory_adjustment.action_start()
        inventory_adjustment.write({
            'line_ids': [
                (0,0, {'product_id': consumed_no_track.id, 'product_qty': 3, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_lot.id, 'product_qty': 3, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'L1', 'product_id': consumed_lot.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S1', 'product_id': consumed_serial.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S2', 'product_id': consumed_serial.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S3', 'product_id': consumed_serial.id}).id, 'location_id': stock_id}),
            ]
        })
        inventory_adjustment.action_validate()
        for finished_product in [finished_no_track, finished_lot, finished_serial]:
            bom = self.env['mrp.bom'].create({
                'product_id': finished_product.id,
                'product_tmpl_id': finished_product.product_tmpl_id.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'product_qty': 1.0,
                'type': 'normal',
                'bom_line_ids': [
                    (0, 0, {'product_id': consumed_no_track.id, 'product_qty': 1}),
                    (0, 0, {'product_id': consumed_lot.id, 'product_qty': 1}),
                    (0, 0, {'product_id': consumed_serial.id, 'product_qty': 1}),
                ],
            })
            
            mo = self.env['mrp.production'].create({
                'name': 'MO %s' % finished_product.tracking,
                'product_id': finished_product.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'product_qty': 1,
                'bom_id': bom.id,
            })
            
            mo.action_assign()

            # Start MO production
            produce_form = Form(self.env['mrp.product.produce'].with_context({
                'active_id': mo.id,
                'active_ids': [mo.id],
            }))

            if finished_product.tracking != 'serial':
                produce_form.product_qty = 1

            if finished_product.tracking != 'none':
                produce_form.lot_id = self.env['stock.production.lot'].create({'name': 'Serial or Lot finished', 'product_id': finished_product.id})
            produce_wizard = produce_form.save()

            produce_wizard.do_produce()
            mo.button_mark_done()

            self.assertEqual(mo.state, 'done', "Production order should be in done state.")

            # Check results of traceability
            context = ({
                'active_id': mo.id,
                'model': 'mrp.production',
            })
            lines = self.env['stock.traceability.report'].with_context(context).get_lines()

            self.assertEqual(len(lines), 1, "Should always return 1 line : the final product")

            final_product = lines[0]
            self.assertEqual(final_product['unfoldable'], True, "Final product should always be unfoldable")

            # Find parts of the final products
            lines = self.env['stock.traceability.report'].get_lines(final_product['id'], **{
                'level': final_product['level'],
                'model_id': final_product['model_id'],
                'model_name': final_product['model'],
            })

            self.assertEqual(len(lines), 3, "There should be 3 lines. 1 for untracked, 1 for lot, and 1 for serial")

            for line in lines:
                tracking = line['columns'][1].split(' ')[1]
                self.assertEqual(
                    line['columns'][-1], "1.000 Unit(s)", 'Part with tracking type "%s", should have quantity = 1' % (tracking)
                )
                unfoldable = False if tracking == 'none' else True
                self.assertEqual(
                    line['unfoldable'],
                    unfoldable,
                    'Parts with tracking type "%s", should have be unfoldable : %s' % (tracking, unfoldable)
                )


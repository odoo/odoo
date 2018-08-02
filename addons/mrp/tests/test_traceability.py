# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon

class TestTraceability(TestMrpCommon):
    TRACKING_TYPES = ['none', 'serial', 'lot']

    def _createBom(self, tracking):
        product = self._createProduct(tracking)
        parts = []
        for tracking_type in self.TRACKING_TYPES:
            part = self._createProduct(tracking_type)
            parts.append((0, 0, {'product_id': part.id, 'product_qty': 1}))

        return self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': parts,
        })

    def _createProduct(self, tracking):
        return self.env['product.product'].create({
            'name': 'Product ' + tracking,
            'type': 'product',
            'tracking': tracking,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def _createLot(self, product):
        return self.env['stock.production.lot'].create({
            'name': '000' + product.id,
            'product_id': product.id,
        })

    def setUp(self):
        super(TestTraceability, self).setUp()
        self.boms = {}

        for tracking_type in self.TRACKING_TYPES:
            self.boms[tracking_type] = self._createBom(tracking_type)

    def test_tracking_types_on_mo(self):
        qty_to_produce = 5
        tracked_qty_str = "1.000 Unit(s)"
        full_qty_str = "%s.000 Unit(s)" % qty_to_produce
        sublines_expected = qty_to_produce + qty_to_produce + 1

        # For each type of tracking
        for tracking_type in self.TRACKING_TYPES:

            # Create a MO
            bom = self.boms[tracking_type]
            mo = self.env['mrp.production'].create({
                'name': 'MO ' + tracking_type,
                'product_id': bom.product_id.id,
                'product_uom_id': self.uom_unit.id,
                'product_qty': 2.0,
                'bom_id': bom.id,
            })

            # Set MO Parts Serial/Lot
            for part in bom.bom_line_ids.product_id:
                if part.tracking != 'none':
                    self.env['stock.quant']._update_available_quantity(part, self.stock_location, 100, lot_id=self._createLot(part))
            mo.action_assign()

            # Start MO production
            produce_form = Form(self.env['mrp.product.produce'].with_context({
                'active_id': mo.id,
                'active_ids': [mo.id],
            }))
            produce_form.product_qty = qty_to_produce
            produce_form.lot_id = self._createLot(bom.product_id)  # Set MO Product Serial/Lot
            produce_wizard = produce_form.save()

            produce_wizard.do_produce()
            mo.button_mark_done()

            self.assertEqual(mo.state, 'done', "Production order should be in done state.")


            # Check results of traceability
            context = ({
                'active_id': produce_wizard.production_id.id,
                'model': 'mrp.production',
            })
            lines = self.env['stock.traceability.report'].with_context(context).get_lines()

            self.assertEqual(len(lines), 1, "Should always return 1 line : the final product")

            final_product = lines[0]
            self.assertEqual(final_product.unfoldable, True, "Final product should always be unfoldable")

            lines = self.env['stock.traceability.report'].get_lines(final_product.id, {
                'level': 31,
                'model_id': final_product.model_id,
                'model_name' : "stock.move.line",
            })


            self.assertEqual(len(lines), sublines_expected, "There should be %s lines. 1 for untracked, and %s for each tracked" % (sublines_expected, qty_to_produce))

            for line in lines:
                if line.lot_id != False:
                    self.assertEqual(line.columns[-1], tracked_qty_str, "When tracked, quantity per line should be 1")
                else:
                    self.assertEqual(line.columns[-1], full_qty_str, "When no lot, quantity per line should be equal to quantity produced")


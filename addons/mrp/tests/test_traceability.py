# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon
import uuid


@tagged('-standard', 'mo_traceability')
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
            'name': 'Product %s' % tracking,
            'type': 'product',
            'tracking': tracking,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def _createLot(self, product):
        return self.env['stock.production.lot'].create({
            'name': 'P%s-%s' % (product.id, uuid.uuid4()),
            'product_id': product.id,
        })

    def setUp(self):
        super(TestTraceability, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')

    def test_tracking_types_on_mo(self):
        # For each type of tracking
        for tracking_type in self.TRACKING_TYPES:
            qty_to_produce = 5 if tracking_type != 'serial' else 1
            qty_by_tracking = {
                'none': qty_to_produce,
                'serial': 1,
                'lot': qty_to_produce,
            }
            sublines_expected = qty_to_produce + 1 + 1

            # Create a MO
            bom = self._createBom(tracking_type)
            mo = self.env['mrp.production'].create({
                'name': 'MO %s' % tracking_type,
                'product_id': bom.product_id.id,
                'product_uom_id': self.uom_unit.id,
                'product_qty': qty_to_produce,
                'bom_id': bom.id,
            })

            # Set MO Parts Serial/Lot
            for line in bom.bom_line_ids:
                part = line.product_id

                # For lots: Create one SN for all parts
                if part.tracking == 'none':
                    self.env['stock.quant']._update_available_quantity(part, self.stock_location, qty_to_produce)

                # For lots: Create one SN for all parts
                if part.tracking == 'lot':
                    lot = self._createLot(part)
                    self.env['stock.quant']._update_available_quantity(part, self.stock_location, qty_to_produce, lot_id=lot)

                # For serial: Create one SN per part
                if part.tracking == 'serial':
                    for n in range(qty_to_produce):
                        lot = self._createLot(part)
                        self.env['stock.quant']._update_available_quantity(part, self.stock_location, 1, lot_id=lot)

            mo.action_assign()

            # Start MO production
            produce_form = Form(self.env['mrp.product.produce'].with_context({
                'active_id': mo.id,
                'active_ids': [mo.id],
            }))
            if tracking_type != 'serial':
                produce_form.product_qty = qty_to_produce

            if tracking_type != 'none':
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
            self.assertEqual(final_product['unfoldable'], True, "Final product should always be unfoldable")

            # Find parts of the final products
            lines = self.env['stock.traceability.report'].get_lines(final_product['id'], **{
                'level': 31,
                'model_id': final_product['model_id'],
                'model_name': "stock.move.line",
            })

            self.assertEqual(
                len(lines),
                sublines_expected,
                "There should be %s lines. 1 for untracked, 1 for lot, and %s for serial" % (sublines_expected, qty_to_produce)
            )

            for line in lines:
                tracking = line['columns'][1].split(' ')[1]
                self.assertEqual(
                    line['columns'][-1],
                    "%s.000 Unit(s)" % qty_by_tracking[tracking],
                    'Part with tracking type "%s", should have quantity = %s' % (tracking, qty_by_tracking[tracking])
                )

                unfoldable = False if tracking == 'none' else True
                self.assertEqual(
                    line['unfoldable'],
                    unfoldable,
                    'Parts with tracking type "%s", should have be unfoldable : %s' % (tracking, unfoldable)
                )


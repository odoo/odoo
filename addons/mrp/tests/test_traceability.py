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
            'location_ids': [(4, stock_id)],
        })
        inventory_adjustment.action_start()
        inventory_adjustment.write({
            'line_ids': [
                (0,0, {'product_id': consumed_no_track.id, 'product_qty': 3, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_lot.id, 'product_qty': 3, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'L1', 'product_id': consumed_lot.id, 'company_id': self.env.company.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S1', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S2', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id, 'location_id': stock_id}),
                (0,0, {'product_id': consumed_serial.id, 'product_qty': 1, 'prod_lot_id': self.env['stock.production.lot'].create({'name': 'S3', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id, 'location_id': stock_id}),
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

            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = finished_product
            mo_form.bom_id = bom
            mo_form.product_uom_id = self.env.ref('uom.product_uom_unit')
            mo_form.product_qty = 1
            mo = mo_form.save()
            mo.action_confirm()
            mo.action_assign()

            # Start MO production
            mo_form = Form(mo)
            mo_form.qty_producing = 1
            if finished_product.tracking != 'none':
                mo_form.lot_producing_id = self.env['stock.production.lot'].create({'name': 'Serial or Lot finished', 'product_id': finished_product.id, 'company_id': self.env.company.id})
            mo = mo_form.save()

            details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.qty_done = 1
            details_operation_form.save()
            details_operation_form = Form(mo.move_raw_ids[2], view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.qty_done = 1
            details_operation_form.save()


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
                    line['columns'][-1], "1.00 Units", 'Part with tracking type "%s", should have quantity = 1' % (tracking)
                )
                unfoldable = False if tracking == 'none' else True
                self.assertEqual(
                    line['unfoldable'],
                    unfoldable,
                    'Parts with tracking type "%s", should have be unfoldable : %s' % (tracking, unfoldable)
                )

    def test_tracking_on_byproducts(self):
        product_final = self.env['product.product'].create({
            'name': 'Finished Product',
            'type': 'product',
            'tracking': 'serial',
        })
        product_1 = self.env['product.product'].create({
            'name': 'Raw 1',
            'type': 'product',
            'tracking': 'serial',
        })
        product_2 = self.env['product.product'].create({
            'name': 'Raw 2',
            'type': 'product',
            'tracking': 'serial',
        })
        byproduct_1 = self.env['product.product'].create({
            'name': 'Byproduct 1',
            'type': 'product',
            'tracking': 'serial',
        })
        byproduct_2 = self.env['product.product'].create({
            'name': 'Byproduct 2',
            'type': 'product',
            'tracking': 'serial',
        })
        bom_1 = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_2.id, 'product_qty': 1})
            ],
            'byproduct_ids': [
                (0, 0, {'product_id': byproduct_1.id, 'product_qty': 1, 'product_uom_id': byproduct_1.uom_id.id}),
                (0, 0, {'product_id': byproduct_2.id, 'product_qty': 1, 'product_uom_id': byproduct_2.uom_id.id})
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_final
        mo_form.bom_id = bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()

        mo_form = Form(mo)
        mo_form.lot_producing_id = self.env['stock.production.lot'].create({
            'product_id': product_final.id,
            'name': 'Final_lot_1',
            'company_id': self.env.company.id,
        })
        mo = mo_form.save()

        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': product_1.id,
                'name': 'Raw_1_lot_1',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': product_2.id,
                'name': 'Raw_2_lot_1',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_finished_ids.filtered(lambda m: m.product_id == byproduct_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': byproduct_1.id,
                'name': 'Byproduct_1_lot_1',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_finished_ids.filtered(lambda m: m.product_id == byproduct_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': byproduct_2.id,
                'name': 'Byproduct_2_lot_1',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        mo_form = Form(mo_backorder)
        mo_form.lot_producing_id = self.env['stock.production.lot'].create({
            'product_id': product_final.id,
            'name': 'Final_lot_2',
            'company_id': self.env.company.id,
        })
        mo_form.qty_producing = 1
        mo_backorder = mo_form.save()

        details_operation_form = Form(
            mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == product_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': product_1.id,
                'name': 'Raw_1_lot_2',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == product_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': product_2.id,
                'name': 'Raw_2_lot_2',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_finished_ids.filtered(lambda m: m.product_id == byproduct_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': byproduct_1.id,
                'name': 'Byproduct_1_lot_2',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_finished_ids.filtered(lambda m: m.product_id == byproduct_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = self.env['stock.production.lot'].create({
                'product_id': byproduct_2.id,
                'name': 'Byproduct_2_lot_2',
                'company_id': self.env.company.id,
            })
            ml.qty_done = 1
        details_operation_form.save()

        mo_backorder.button_mark_done()

        # self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 4)
        # self.assertEqual(len(mo.move_finished_ids.mapped('move_line_ids')), 6)

        mo = mo | mo_backorder
        raw_move_lines = mo.move_raw_ids.mapped('move_line_ids')
        raw_line_raw_1_lot_1 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_1_lot_1')
        self.assertEqual(set(raw_line_raw_1_lot_1.produce_line_ids.lot_id.mapped('name')), set(['Final_lot_1', 'Byproduct_1_lot_1', 'Byproduct_2_lot_1']))
        raw_line_raw_2_lot_1 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_2_lot_1')
        self.assertEqual(set(raw_line_raw_2_lot_1.produce_line_ids.lot_id.mapped('name')), set(['Final_lot_1', 'Byproduct_1_lot_1', 'Byproduct_2_lot_1']))

        finished_move_lines = mo.move_finished_ids.mapped('move_line_ids')
        finished_move_line_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Final_lot_1')
        self.assertEqual(finished_move_line_lot_1.consume_line_ids.filtered(lambda l: l.qty_done), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        finished_move_line_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Final_lot_2')
        raw_line_raw_1_lot_2 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_1_lot_2')
        raw_line_raw_2_lot_2 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_2_lot_2')
        self.assertEqual(finished_move_line_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

        byproduct_move_line_1_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_1_lot_1')
        self.assertEqual(byproduct_move_line_1_lot_1.consume_line_ids.filtered(lambda l: l.qty_done), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        byproduct_move_line_1_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_1_lot_2')
        self.assertEqual(byproduct_move_line_1_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

        byproduct_move_line_2_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_2_lot_1')
        self.assertEqual(byproduct_move_line_2_lot_1.consume_line_ids.filtered(lambda l: l.qty_done), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        byproduct_move_line_2_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_2_lot_2')
        self.assertEqual(byproduct_move_line_2_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

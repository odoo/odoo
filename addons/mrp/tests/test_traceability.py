# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
import logging

_logger = logging.getLogger(__name__)


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
        Lot = self.env['stock.production.lot']
        # create inventory
        quants = self.env['stock.quant'].create({
            'location_id': stock_id,
            'product_id': consumed_no_track.id,
            'inventory_quantity': 3
        })
        quants |= self.env['stock.quant'].create({
            'location_id': stock_id,
            'product_id': consumed_lot.id,
            'inventory_quantity': 3,
            'lot_id': Lot.create({'name': 'L1', 'product_id': consumed_lot.id, 'company_id': self.env.company.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': stock_id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S1', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': stock_id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S2', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': stock_id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S3', 'product_id': consumed_serial.id, 'company_id': self.env.company.id}).id
        })
        quants.action_apply_inventory()

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

    def test_reuse_unbuilt_usn(self):
        """
        Produce a SN product
        Unbuilt it
        Produce a new SN product with same lot
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_base_1=1, qty_base_2=1, qty_final=1, tracking_final='serial')
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(p1, stock_location, 1)
        self.env['stock.quant']._update_available_quantity(p2, stock_location, 1)
        mo.action_assign()

        lot = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
            'company_id': self.env.company.id,
        })

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo_form.lot_producing_id = lot
        mo = mo_form.save()
        mo.button_mark_done()

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo
        unbuild_form.lot_id = lot
        unbuild_form.save().action_unbuild()

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo = mo_form.save()
        mo.action_confirm()

        with self.assertLogs(level="WARNING") as log_catcher:
            mo_form = Form(mo)
            mo_form.qty_producing = 1.0
            mo_form.lot_producing_id = lot
            mo = mo_form.save()
            _logger.warning('Dummy')
        self.assertEqual(len(log_catcher.output), 1, "Useless warnings: \n%s" % "\n".join(log_catcher.output[:-1]))

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_tracked_and_manufactured_component(self):
        """
        Suppose this structure:
            productA --|- 1 x productB --|- 1 x productC
            with productB tracked by lot
        Ensure that, when we already have some qty of productB (with different lots),
        the user can produce several productA and can then produce some productB again
        """
        stock_location = self.env.ref('stock.stock_location_stock')

        productA, productB, productC = self.env['product.product'].create([{
            'name': 'Product A',
            'type': 'product',
        }, {
            'name': 'Product B',
            'type': 'product',
            'tracking': 'lot',
        }, {
            'name': 'Product C',
            'type': 'consu',
        }])

        lot_B01, lot_B02, lot_B03 = self.env['stock.production.lot'].create([{
            'name': 'lot %s' % i,
            'product_id': productB.id,
            'company_id': self.env.company.id,
        } for i in [1, 2, 3]])

        self.env['mrp.bom'].create([{
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1})],
        } for finished, component in [(productA, productB), (productB, productC)]])

        self.env['stock.quant']._update_available_quantity(productB, stock_location, 10, lot_id=lot_B01)
        self.env['stock.quant']._update_available_quantity(productB, stock_location, 5, lot_id=lot_B02)

        # Produce 15 x productA
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = productA
        mo_form.product_qty = 15
        mo = mo_form.save()
        mo.action_confirm()
        action = mo.button_mark_done()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        # Produce 15 x productB
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = productB
        mo_form.product_qty = 15
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 15
        mo_form.lot_producing_id = lot_B03
        mo = mo_form.save()
        mo.button_mark_done()

        self.assertEqual(lot_B01.product_qty, 0)
        self.assertEqual(lot_B02.product_qty, 0)
        self.assertEqual(lot_B03.product_qty, 15)
        self.assertEqual(productA.qty_available, 15)

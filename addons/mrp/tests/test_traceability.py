# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.exceptions import UserError

from datetime import datetime
import logging
from freezegun import freeze_time

_logger = logging.getLogger(__name__)


class TestTraceability(TestMrpCommon):
    TRACKING_TYPES = ['none', 'serial', 'lot']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

    def _create_product(self, tracking):
        return self.env['product.product'].create({
            'name': 'Product %s' % tracking,
            'is_storable': True,
            'tracking': tracking,
        })

    def test_tracking_types_on_mo(self):
        finished_no_track = self._create_product('none')
        finished_lot = self._create_product('lot')
        finished_serial = self._create_product('serial')
        consumed_no_track = self._create_product('none')
        consumed_lot = self._create_product('lot')
        consumed_serial = self._create_product('serial')
        Lot = self.env['stock.lot']
        # create inventory
        quants = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': consumed_no_track.id,
            'inventory_quantity': 3
        })
        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': consumed_lot.id,
            'inventory_quantity': 3,
            'lot_id': Lot.create({'name': 'L1', 'product_id': consumed_lot.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S1', 'product_id': consumed_serial.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S2', 'product_id': consumed_serial.id}).id
        })
        quants |= self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': consumed_serial.id,
            'inventory_quantity': 1,
            'lot_id': Lot.create({'name': 'S3', 'product_id': consumed_serial.id}).id
        })
        quants.action_apply_inventory()

        for finished_product in [finished_no_track, finished_lot, finished_serial]:
            bom = self.env['mrp.bom'].create({
                'product_id': finished_product.id,
                'product_tmpl_id': finished_product.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
                'product_qty': 1.0,
                'type': 'normal',
                'bom_line_ids': [
                    Command.create({'product_id': consumed_no_track.id, 'product_qty': 1}),
                    Command.create({'product_id': consumed_lot.id, 'product_qty': 1}),
                    Command.create({'product_id': consumed_serial.id, 'product_qty': 1}),
                ],
            })

            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = finished_product
            mo_form.bom_id = bom
            mo_form.product_uom_id = self.uom_unit
            mo_form.product_qty = 1
            mo = mo_form.save()
            mo.action_confirm()
            mo.action_assign()

            # Start MO production
            mo_form = Form(mo)
            if finished_product.tracking != 'none':
                mo_form.lot_producing_ids.set(self.env['stock.lot'].create({'name': 'Serial or Lot finished', 'product_id': finished_product.id}))
            mo = mo_form.save()

            details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 1
            details_operation_form.save()
            details_operation_form = Form(mo.move_raw_ids[2], view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.quantity = 1
            details_operation_form.save()
            mo.move_raw_ids.picked = True

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
            'is_storable': True,
            'tracking': 'serial',
        })
        product_1 = self.env['product.product'].create({
            'name': 'Raw 1',
            'is_storable': True,
            'tracking': 'serial',
        })
        product_2 = self.env['product.product'].create({
            'name': 'Raw 2',
            'is_storable': True,
            'tracking': 'serial',
        })
        byproduct_1 = self.env['product.product'].create({
            'name': 'Byproduct 1',
            'is_storable': True,
            'tracking': 'serial',
        })
        byproduct_2 = self.env['product.product'].create({
            'name': 'Byproduct 2',
            'is_storable': True,
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
                Command.create({'product_id': product_1.id, 'product_qty': 1}),
                Command.create({'product_id': product_2.id, 'product_qty': 1}),
            ],
            'byproduct_ids': [
                Command.create({'product_id': byproduct_1.id, 'product_qty': 1, 'product_uom_id': byproduct_1.uom_id.id}),
                Command.create({'product_id': byproduct_2.id, 'product_qty': 1, 'product_uom_id': byproduct_2.uom_id.id}),
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_final
        mo_form.bom_id = bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()

        mo.lot_producing_ids = self.env['stock.lot'].create({
            'product_id': product_final.id,
            'name': 'Final_lot_1',
        })
        mo.qty_producing = 1
        mo.set_qty_producing()

        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': product_1.id,
                'name': 'Raw_1_lot_1',
            })
        details_operation_form.save()
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': product_2.id,
                'name': 'Raw_2_lot_1',
            })
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_finished_ids.filtered(lambda m: m.product_id == byproduct_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': byproduct_1.id,
                'name': 'Byproduct_1_lot_1',
            })
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_finished_ids.filtered(lambda m: m.product_id == byproduct_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': byproduct_2.id,
                'name': 'Byproduct_2_lot_1',
            })
        details_operation_form.save()

        mo.move_raw_ids.picked = True
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.production_group_id.production_ids[-1]
        mo_form = Form(mo_backorder)
        mo_form.lot_producing_ids.set(self.env['stock.lot'].create({
            'product_id': product_final.id,
            'name': 'Final_lot_2',
        }))
        mo_backorder = mo_form.save()

        details_operation_form = Form(
            mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == product_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': product_1.id,
                'name': 'Raw_1_lot_2',
            })
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == product_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': product_2.id,
                'name': 'Raw_2_lot_2',
            })
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_finished_ids.filtered(lambda m: m.product_id == byproduct_1),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': byproduct_1.id,
                'name': 'Byproduct_1_lot_2',
            })
        details_operation_form.save()
        details_operation_form = Form(
            mo_backorder.move_finished_ids.filtered(lambda m: m.product_id == byproduct_2),
            view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.env['stock.lot'].create({
                'product_id': byproduct_2.id,
                'name': 'Byproduct_2_lot_2',
            })
        details_operation_form.save()

        mo_backorder.move_raw_ids.picked = True
        mo_backorder.button_mark_done()

        mo = mo | mo_backorder
        raw_move_lines = mo.move_raw_ids.mapped('move_line_ids')
        raw_line_raw_1_lot_1 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_1_lot_1')
        self.assertEqual(set(raw_line_raw_1_lot_1.produce_line_ids.lot_id.mapped('name')), set(['Final_lot_1', 'Byproduct_1_lot_1', 'Byproduct_2_lot_1']))
        raw_line_raw_2_lot_1 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_2_lot_1')
        self.assertEqual(set(raw_line_raw_2_lot_1.produce_line_ids.lot_id.mapped('name')), set(['Final_lot_1', 'Byproduct_1_lot_1', 'Byproduct_2_lot_1']))

        finished_move_lines = mo.move_finished_ids.mapped('move_line_ids')
        finished_move_line_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Final_lot_1')
        self.assertEqual(finished_move_line_lot_1.consume_line_ids.filtered(lambda l: l.quantity), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        finished_move_line_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Final_lot_2')
        raw_line_raw_1_lot_2 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_1_lot_2')
        raw_line_raw_2_lot_2 = raw_move_lines.filtered(lambda ml: ml.lot_id.name == 'Raw_2_lot_2')
        self.assertEqual(finished_move_line_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

        byproduct_move_line_1_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_1_lot_1')
        self.assertEqual(byproduct_move_line_1_lot_1.consume_line_ids.filtered(lambda l: l.quantity), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        byproduct_move_line_1_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_1_lot_2')
        self.assertEqual(byproduct_move_line_1_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

        byproduct_move_line_2_lot_1 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_2_lot_1')
        self.assertEqual(byproduct_move_line_2_lot_1.consume_line_ids.filtered(lambda l: l.quantity), raw_line_raw_1_lot_1 | raw_line_raw_2_lot_1)
        byproduct_move_line_2_lot_2 = finished_move_lines.filtered(lambda ml: ml.lot_id.name == 'Byproduct_2_lot_2')
        self.assertEqual(byproduct_move_line_2_lot_2.consume_line_ids, raw_line_raw_1_lot_2 | raw_line_raw_2_lot_2)

    def test_reuse_unbuilt_usn(self):
        """
        Produce a SN product
        Unbuilt it
        Produce a new SN product with same lot
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_base_1=1, qty_base_2=1, qty_final=1, tracking_final='serial')
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1)
        mo.action_assign()

        lot = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
        })

        mo_form = Form(mo)
        mo_form.lot_producing_ids.set(lot)
        mo = mo_form.save()
        mo.move_raw_ids.picked = True
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
            mo_form.lot_producing_ids.set(lot)
            mo = mo_form.save()
            _logger.warning('Dummy')
        self.assertEqual(len(log_catcher.output), 1, "Useless warnings: \n%s" % "\n".join(log_catcher.output[:-1]))

        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_tracked_and_manufactured_component(self):
        """ Suppose this structure:
            productA --|- 1 x productB --|- 1 x productC
            with productB tracked by lot
        Ensure that, when we already have some qty of productB (with different lots),
        the user can produce several productA and can then produce some productB again
        """
        productA, productB, productC = self.env['product.product'].create([{
            'name': 'Product A',
            'is_storable': True,
        }, {
            'name': 'Product B',
            'is_storable': True,
            'tracking': 'lot',
        }, {
            'name': 'Product C',
            'type': 'consu',
        }])

        lot_B01, lot_B02, lot_B03 = self.env['stock.lot'].create([{
            'name': 'lot %s' % i,
            'product_id': productB.id,
        } for i in [1, 2, 3]])

        self.env['mrp.bom'].create([{
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1})],
        } for finished, component in [(productA, productB), (productB, productC)]])

        self.env['stock.quant']._update_available_quantity(productB, self.stock_location, 10, lot_id=lot_B01)
        self.env['stock.quant']._update_available_quantity(productB, self.stock_location, 5, lot_id=lot_B02)

        # Produce 15 x productA
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = productA
        mo_form.product_qty = 15
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_mark_done()

        # Produce 15 x productB
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = productB
        mo_form.product_qty = 15
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 15
        mo_form.lot_producing_ids.set(lot_B03)
        mo = mo_form.save()
        mo.lot_producing_ids = lot_B03
        mo.button_mark_done()

        self.assertEqual(lot_B01.product_qty, 0)
        self.assertEqual(lot_B02.product_qty, 0)
        self.assertEqual(lot_B03.product_qty, 15)
        self.assertEqual(productA.qty_available, 15)

    def test_last_delivery_traceability(self):
        """
        Suppose this structure (-> means 'produces')
        1 x Subcomponent A -> 1 x Component A -> 1 x EndProduct A
        All three tracked by lots. Ensure that after validating Picking A (out)
        for EndProduct A, all three lots' delivery_ids are set to
        Picking A.
        """
        # Create the three lot-tracked products.
        subcomponentA = self._create_product('lot')
        componentA = self._create_product('lot')
        endproductA = self._create_product('lot')

        # Create production lots.
        lot_subcomponentA, lot_componentA, lot_endProductA = self.env['stock.lot'].create([{
            'name': 'lot %s' % product,
            'product_id': product.id,
        } for product in (subcomponentA, componentA, endproductA)])

        # Create two boms, one for Component A and one for EndProduct A
        self.env['mrp.bom'].create([{
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1})],
        } for finished, component in [(endproductA, componentA), (componentA, subcomponentA)]])

        self.env['stock.quant']._update_available_quantity(subcomponentA, self.stock_location, 1, lot_id=lot_subcomponentA)

        # Produce 1 component A
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = componentA
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.lot_producing_ids.set(lot_componentA)
        mo = mo_form.save()
        mo.move_raw_ids.picked = True
        mo.button_mark_done()

        # Produce 1 endProduct A
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = endproductA
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.lot_producing_ids.set(lot_endProductA)
        mo = mo_form.save()
        mo.move_raw_ids[0].write({'quantity': 1.0, 'picked': True})
        mo.button_mark_done()

        # Create out picking for EndProduct A
        pickingA_out = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        moveA = self.env['stock.move'].create({
            'product_id': endproductA.id,
            'quantity': 1,
            'product_uom': endproductA.uom_id.id,
            'picking_id': pickingA_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        # Set move_line lot_id to the mrp.production lot_producing_id
        moveA.move_line_ids[0].write({
            'quantity': 1.0,
            'lot_id': lot_endProductA.id,
        })
        # Transfer picking
        moveA.picked = True
        pickingA_out._action_done()

        # Use concat so that delivery_ids is computed in batch.
        for lot in lot_subcomponentA.concat(lot_componentA, lot_endProductA):
            self.assertEqual(lot.delivery_ids.ids, pickingA_out.ids)

    def test_unbuild_scrap_and_unscrap_tracked_component(self):
        """
        Suppose a tracked-by-SN component C. There is one C in stock with SN01.
        Build a product P that uses C with SN, unbuild P, scrap SN, unscrap SN
        and rebuild a product with SN in the components
        """
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'is_storable': True,
            'tracking': 'serial',
        })
        serial_number = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': 'Super Serial',
        })
        self.env['stock.quant']._update_available_quantity(component, self.stock_location, 1, lot_id=serial_number)

        # produce 1
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.move_line_ids.lot_id, serial_number)

        with Form(mo) as mo_form:
            mo_form.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.button_mark_done()

        # unbuild
        Form.from_action(self.env, mo.button_unbuild()).save().action_validate()

        # scrap the component
        scrap = self.env['stock.scrap'].create({
            'product_id': component.id,
            'product_uom_id': component.uom_id.id,
            'location_id': self.stock_location.id,
            'scrap_qty': 1,
            'lot_id': serial_number.id,
        })
        scrap_location = scrap.scrap_location_id
        scrap.do_scrap()

        # unscrap the component
        internal_move = self.env['stock.move'].create({
            'location_id': scrap_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': component.id,
            'product_uom': component.uom_id.id,
            'product_uom_qty': 1.0,
            'picked': True,
            'move_line_ids': [Command.create({
                'product_id': component.id,
                'location_id': scrap_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': component.uom_id.id,
                'quantity': 1.0,
                'lot_id': serial_number.id,
            })],
        })
        internal_move._action_confirm()
        internal_move._action_done()

        # produce one with the unscrapped component
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.move_line_ids.lot_id, serial_number)

        with Form(mo) as mo_form:
            mo_form.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.picked = True
        mo.button_mark_done()

        self.assertRecordValues((mo.move_finished_ids + mo.move_raw_ids).move_line_ids, [
            {'product_id': self.bom_4.product_id.id, 'lot_id': False, 'quantity': 1},
            {'product_id': component.id, 'lot_id': serial_number.id, 'quantity': 1},
        ])

    def test_generate_serial_button(self):
        """Test if lot in form "00000dd" is manually created, the generate serial
        button can skip it and create the next one.
        """
        mo, _bom, p_final, _p1, _p2 = self.generate_mo(qty_base_1=1, qty_base_2=1, qty_final=1, tracking_final='lot')

        # generate lot lot_0 on MO
        mo.action_generate_serial()
        lot_0 = mo.lot_producing_ids[:1].name
        # manually create lot_1 (lot_0 + 1)
        lot_1 = self.env['stock.lot'].create({
            'name': str(int(lot_0) + 1).zfill(7),
            'product_id': p_final.id,
        }).name
        # generate lot lot_2 on a new MO
        mo = mo.copy()
        mo.action_confirm()
        mo.action_generate_serial()
        lot_2 = mo.lot_producing_ids.name
        self.assertEqual(lot_2, str(int(lot_1) + 1).zfill(7))

    def test_generate_serial_button_sequence(self):
        """Test if serial in form "00000dd" is manually created, the generate serial
        correctly create new serial from sequence.
        """
        mo, _bom, p_final, _p1, _p2 = self.generate_mo(qty_base_1=1, qty_base_2=1, qty_final=1, tracking_final='serial')
        p_final.serial_prefix_format = 'TEST/'

        # manually create lot_1
        self.env['stock.lot'].create({
            'name': 'TEST/0000001',
            'product_id': p_final.id,
        })

        # generate serial lot_2 from the MO (next_serial)
        mo.action_generate_serial()
        self.assertEqual(mo.lot_producing_ids[:1].name, "TEST/0000002")

        p_final.lot_sequence_id.prefix = 'xx%(doy)sxx'
        # generate serial lot_3 from the MO (next from sequence)
        mo.lot_producing_ids = self.env['stock.lot']
        mo.action_generate_serial()
        self.assertIn(datetime.now().strftime('%j'), mo.lot_producing_ids.name)

    def test_assign_stock_move_date_on_mark_done(self):
        product_final = self.env['product.product'].create({
            'name': 'Finished Product',
            'is_storable': True,
        })
        with freeze_time('2024-01-15'):
            production = self.env['mrp.production'].create({
                'product_id': product_final.id,
                'product_qty': 1,
                'date_start': datetime(2024, 1, 10)
            })
            production.action_confirm()
            production.qty_producing = 1
            production.button_mark_done()
            self.assertEqual(production.move_finished_ids.date, datetime(2024, 1, 15), "Stock move should be availbale after the production is done.")

    def test_use_lot_already_consumed(self):
        """
        Tracked-by-sn product
        Produce SN
        Consume SN
        Consume SN -> Should raise an error as it has already been consumed
        """
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        sn_lot01, sn_lot02 = self.env['stock.lot'].create([{
            'product_id': component.id,
            'name': name,
            'company_id': self.env.company.id,
        } for name in ['SN01', 'SN02']])
        self.env['stock.quant']._update_available_quantity(component, self.stock_location, 1, lot_id=sn_lot02)

        mo = self.env['mrp.production'].create({
            'product_id': component.id,
            'product_qty': 1,
            'product_uom_id': component.uom_id.id,
            'company_id': self.env.company.id,
        })
        mo.action_confirm()
        mo.lot_producing_ids = sn_lot01
        mo.button_mark_done()
        self.assertRecordValues(mo.move_finished_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn_lot01.id, 'quantity': 1.0, 'state': 'done'},
        ])

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.move_line_ids.lot_id = sn_lot01
        mo.move_raw_ids.move_line_ids.picked = True
        mo.button_mark_done()
        self.assertRecordValues(mo.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn_lot01.id, 'quantity': 1.0, 'state': 'done'},
        ])

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.move_line_ids.lot_id = sn_lot01
        mo.move_raw_ids.move_line_ids.picked = True
        with self.assertRaises(UserError):
            mo.button_mark_done()

    def test_produce_consume_unbuild_and_consume(self):
        """
        (1) Produce SN
        (2) Consume SN
        Unbuild (2)
        Consume SN
        -> We should not raise any UserError
        """
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        sn = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': "SN",
            'company_id': self.env.company.id,
        })

        mo_produce_sn = self.env['mrp.production'].create({
            'product_id': component.id,
            'product_qty': 1,
            'product_uom_id': component.uom_id.id,
            'company_id': self.env.company.id,
        })
        mo_produce_sn.action_confirm()
        mo_produce_sn.lot_producing_ids = sn
        mo_produce_sn.button_mark_done()

        mo_consume_sn_form = Form(self.env['mrp.production'])
        mo_consume_sn_form.bom_id = self.bom_4
        mo_consume_sn = mo_consume_sn_form.save()
        mo_consume_sn.action_confirm()
        mo_consume_sn.qty_producing = 1
        mo_consume_sn.move_raw_ids.move_line_ids.quantity = 1
        mo_consume_sn.move_raw_ids.move_line_ids.lot_id = sn
        mo_consume_sn.move_raw_ids.move_line_ids.picked = True
        mo_consume_sn.button_mark_done()
        self.assertRecordValues(mo_consume_sn.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn.id, 'quantity': 1.0, 'state': 'done'},
        ])

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo_consume_sn
        unbuild_form.save().action_unbuild()

        mo_consume_sn_form = Form(self.env['mrp.production'])
        mo_consume_sn_form.bom_id = self.bom_4
        mo_consume_sn = mo_consume_sn_form.save()
        mo_consume_sn.action_confirm()
        mo_consume_sn.qty_producing = 1
        mo_consume_sn.move_raw_ids.move_line_ids.quantity = 1
        mo_consume_sn.move_raw_ids.move_line_ids.lot_id = sn
        mo_consume_sn.move_raw_ids.move_line_ids.picked = True
        mo_consume_sn.button_mark_done()
        self.assertRecordValues(mo_consume_sn.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn.id, 'quantity': 1.0, 'state': 'done'},
        ])

    def test_produce_consume_unbuild_all_and_consume(self):
        """
        (1) Produce SN
        (2) Consume SN
        Unbuild (2)
        Unbuild (1)
        Update stock with 1 SN
        Consume SN
        -> We should not raise any UserError
        """
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        sn = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': "SN",
            'company_id': self.env.company.id,
        })

        mo_produce_sn = self.env['mrp.production'].create({
            'product_id': component.id,
            'product_qty': 1,
            'product_uom_id': component.uom_id.id,
            'company_id': self.env.company.id,
        })
        mo_produce_sn.action_confirm()
        mo_produce_sn.lot_producing_ids = sn
        mo_produce_sn.button_mark_done()

        mo_consume_sn_form = Form(self.env['mrp.production'])
        mo_consume_sn_form.bom_id = self.bom_4
        mo_consume_sn = mo_consume_sn_form.save()
        mo_consume_sn.action_confirm()
        mo_consume_sn.qty_producing = 1
        mo_consume_sn.move_raw_ids.move_line_ids.quantity = 1
        mo_consume_sn.move_raw_ids.move_line_ids.lot_id = sn
        mo_consume_sn.move_raw_ids.move_line_ids.picked = True
        mo_consume_sn.button_mark_done()
        self.assertRecordValues(mo_consume_sn.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn.id, 'quantity': 1.0, 'state': 'done'},
        ])

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo_consume_sn
        unbuild_form.save().action_unbuild()

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo_produce_sn
        unbuild_form.lot_id = sn
        unbuild_form.save().action_unbuild()

        self.env['stock.quant']._update_available_quantity(component, self.stock_location, 1, lot_id=sn)

        mo_consume_sn_form = Form(self.env['mrp.production'])
        mo_consume_sn_form.bom_id = self.bom_4
        mo_consume_sn = mo_consume_sn_form.save()
        mo_consume_sn.action_confirm()
        mo_consume_sn.qty_producing = 1
        mo_consume_sn.move_raw_ids.move_line_ids.quantity = 1
        mo_consume_sn.move_raw_ids.move_line_ids.lot_id = sn
        mo_consume_sn.move_raw_ids.move_line_ids.picked = True
        mo_consume_sn.button_mark_done()
        self.assertRecordValues(mo_consume_sn.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn.id, 'quantity': 1.0, 'state': 'done'},
        ])

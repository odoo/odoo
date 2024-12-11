# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon

@tagged('post_install', '-at_install')
class TestRepairTraceability(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

    def test_tracking_repair_production(self):
        """
        Test that removing a tracked component with a repair does not block the flow of using that component in another
        bom
        """
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]
        picking_type.use_auto_consume_components_lots = True
        product_to_repair = self.env['product.product'].create({
            'name': 'product first serial to act repair',
            'tracking': 'serial',
        })
        ptrepair_lot = self.env['stock.lot'].create({
            'name': 'A1',
            'product_id': product_to_repair.id,
            'company_id': self.env.user.company_id.id
        })
        product_to_remove = self.env['product.product'].create({
            'name': 'other first serial to remove with repair',
            'tracking': 'serial',
        })
        ptremove_lot = self.env['stock.lot'].create({
            'name': 'B2',
            'product_id': product_to_remove.id,
            'company_id': self.env.user.company_id.id
        })
        # Create a manufacturing order with product (with SN A1)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_repair
        with mo_form.move_raw_ids.new() as move:
            move.product_id = product_to_remove
            move.product_uom_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        # Set serial to A1
        mo.lot_producing_id = ptrepair_lot
        # Set component serial to B2
        mo.move_raw_ids.move_line_ids.lot_id = ptremove_lot
        mo.move_raw_ids.picked = True
        mo.button_mark_done()

        with Form(self.env['repair.order']) as ro_form:
            ro_form.product_id = product_to_repair
            ro_form.lot_id = ptrepair_lot  # Repair product Serial A1
            with ro_form.move_ids.new() as operation:
                operation.repair_line_type = 'remove'
                operation.product_id = product_to_remove
            ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = ptremove_lot # Remove product Serial B2 from the product.
        ro.action_repair_start()
        ro.move_ids.picked = True
        ro.action_repair_end()

        # Create a manufacturing order with product (with SN A2)
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = product_to_repair
        with mo2_form.move_raw_ids.new() as move:
            move.product_id = product_to_remove
            move.product_uom_qty = 1
        mo2 = mo2_form.save()
        mo2.action_confirm()
        # Set serial to A2
        mo2.lot_producing_id = self.env['stock.lot'].create({
            'name': 'A2',
            'product_id': product_to_repair.id,
            'company_id': self.env.user.company_id.id
        })
        # Set component serial to B2 again, it is possible
        mo2.move_raw_ids.move_line_ids.lot_id = ptremove_lot
        mo2.move_raw_ids.picked = True
        # We are not forbidden to use that serial number, so nothing raised here
        mo2.button_mark_done()

    def test_mo_with_used_sn_component(self):
        """
        Suppose a tracked-by-usn component has been used to produce a product. Then, using a repair order,
        this component is removed from the product and returned as available stock. The user should be able to
        use the component in a new MO
        """
        def produce_one(product, component):
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = product
            with mo_form.move_raw_ids.new() as raw_line:
                raw_line.product_id = component
                raw_line.product_uom_qty = 1
            mo = mo_form.save()
            mo.action_confirm()
            mo.action_assign()
            mo.move_raw_ids.picked = True
            mo.button_mark_done()
            return mo

        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]
        picking_type.use_auto_consume_components_lots = True

        stock_location = self.env.ref('stock.stock_location_stock')

        finished, component = self.env['product.product'].create([{
            'name': 'Finished Product',
            'type': 'product',
        }, {
            'name': 'SN Componentt',
            'type': 'product',
            'tracking': 'serial',
        }])

        sn_lot = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': 'USN01',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(component, stock_location, 1, lot_id=sn_lot)

        mo = produce_one(finished, component)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = finished
        with ro_form.move_ids.new() as ro_line:
            ro_line.repair_line_type = 'recycle'
            ro_line.product_id = component
        ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = sn_lot
        ro.action_repair_start()
        ro.move_ids.picked = True
        ro.action_repair_end()
        mo = produce_one(finished, component)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)
        # Now, we will test removing the component and putting it back in stock,
        # then placing it back into the product and removing it a second time.
        # The user should be able to use the component in a new MO.
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = finished
        with ro_form.move_ids.new() as ro_line:
            ro_line.repair_line_type = 'recycle'
            ro_line.product_id = component
            ro_line.location_dest_id = stock_location
        ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = sn_lot
        ro.action_repair_start()
        ro.action_repair_end()
        self.assertEqual(ro.state, 'done')
        # Add the component into the product
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = finished
        with ro_form.move_ids.new() as ro_line:
            ro_line.repair_line_type = 'add'
            ro_line.product_id = component
            ro_line.location_id = stock_location
        ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = sn_lot
        ro.action_repair_start()
        ro.action_repair_end()
        self.assertEqual(ro.state, 'done')
        # Removing it a second time
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = finished
        with ro_form.move_ids.new() as ro_line:
            ro_line.repair_line_type = 'recycle'
            ro_line.product_id = component
            ro_line.location_dest_id = stock_location
        ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = sn_lot
        ro.action_repair_start()
        ro.action_repair_end()
        self.assertEqual(ro.state, 'done')
        # check if the removed component can be used in a new MO
        mo = produce_one(finished, component)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)

    def test_mo_with_used_sn_component_02(self):
        """
        Suppose a tracked-by-usn component has been remvoed in a repair order. Then, using to produce a product,
        but this product has been unbuild. The user should be able to use the component in a new MO
        """
        finished, component = self.env['product.product'].create([{
            'name': 'Finished Product',
            'type': 'product',
        }, {
            'name': 'SN Componentt',
            'type': 'product',
            'tracking': 'serial',
        }])

        sn_lot = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': 'USN01',
            'company_id': self.env.company.id,
        })

        # create a repair order
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = self.product_1
        with ro_form.move_ids.new() as ro_line:
            ro_line.repair_line_type = 'remove'
            ro_line.product_id = component
        ro = ro_form.save()
        ro.action_validate()
        ro.move_ids[0].lot_ids = sn_lot
        ro.action_repair_start()
        ro.action_repair_end()

        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(component, stock_location, 1, lot_id=sn_lot)
        self.assertEqual(component.qty_available, 1)

        # create a manufacturing order
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished
        with mo_form.move_raw_ids.new() as raw_line:
            raw_line.product_id = component
            raw_line.product_uom_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)
        # unbuild the mo
        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo
        unbuild_form.save().action_unbuild()
        # create another mo and use the same SN
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished
        with mo_form.move_raw_ids.new() as raw_line:
            raw_line.product_id = component
            raw_line.product_uom_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)

    def test_mo_with_unscrapped_tracked_component(self):
        """
        Tracked-by-sn component
        Use it in a MO
        Repair the finished product:
            Remove the component, destination: scrap location
        Move the component back to the stock
        Use it in a MO
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        scrap_location = self.env['stock.location'].search([('company_id', '=', self.env.company.id), ('scrap_location', '=', True)], limit=1)

        finished = self.bom_4.product_id
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'type': 'product',
            'tracking': 'serial',
        })

        sn_lot = self.env['stock.lot'].create({
            'product_id': component.id,
            'name': 'SN01',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(component, stock_location, 1, lot_id=sn_lot)

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.move_line_ids.picked = True
        mo.button_mark_done()

        ro = self.env['repair.order'].create({
            'product_id': finished.id,
            'picking_type_id': self.warehouse_1.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'name': 'foo',
                    'product_id': component.id,
                    'lot_ids': [(4, sn_lot.id)],
                    'repair_line_type': 'remove',
                    'location_dest_id': scrap_location.id,
                    'price_unit': 0,
                })
            ],
        })
        ro.action_validate()
        ro.action_repair_start()
        ro.action_repair_end()

        sm = self.env['stock.move'].create({
            'name': component.name,
            'product_id': component.id,
            'product_uom_qty': 1,
            'product_uom': component.uom_id.id,
            'location_id': scrap_location.id,
            'location_dest_id': stock_location.id,
        })
        sm._action_confirm()
        sm.move_line_ids.write({
            'quantity': 1.0,
            'lot_id': sn_lot.id,
            'picked': True,
        })
        sm._action_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = 1
        mo.move_raw_ids.move_line_ids.quantity = 1
        mo.move_raw_ids.move_line_ids.picked = True
        mo.button_mark_done()

        self.assertRecordValues(mo.move_raw_ids.move_line_ids, [
            {'product_id': component.id, 'lot_id': sn_lot.id, 'quantity': 1.0, 'state': 'done'},
        ])

    def test_repair_with_consumable_kit(self):
        """Test that a consumable kit can be repaired."""
        self.assertEqual(self.bom_2.type, 'phantom')
        kit_product = self.bom_2.product_id
        kit_product.type = 'consu'
        self.assertEqual(kit_product.type, 'consu')
        ro = self.env['repair.order'].create({
            'product_id': kit_product.id,
            'picking_type_id': self.warehouse_1.repair_type_id.id,
        })
        ro.action_validate()
        ro.action_repair_start()
        ro.action_repair_end()
        self.assertEqual(ro.state, 'done')

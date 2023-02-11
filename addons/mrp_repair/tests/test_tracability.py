# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon

@tagged('post_install', '-at_install')
class TestRepairTraceability(TestMrpCommon):

    def test_tracking_repair_production(self):
        """
        Test that removing a tracked component with a repair does not block the flow of using that component in another
        bom
        """
        product_to_repair = self.env['product.product'].create({
            'name': 'product first serial to act repair',
            'tracking': 'serial',
        })
        ptrepair_lot = self.env['stock.production.lot'].create({
            'name': 'A1',
            'product_id': product_to_repair.id,
            'company_id': self.env.user.company_id.id
        })
        product_to_remove = self.env['product.product'].create({
            'name': 'other first serial to remove with repair',
            'tracking': 'serial',
        })
        ptremove_lot = self.env['stock.production.lot'].create({
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
            move.move_line_ids.lot_id = ptremove_lot  # Set component serial to B2
        mo = mo_form.save()
        mo.action_confirm()
        # Set serial to A1
        mo.lot_producing_id = ptrepair_lot
        mo.button_mark_done()

        with Form(self.env['repair.order']) as ro_form:
            ro_form.product_id = product_to_repair
            ro_form.lot_id = ptrepair_lot  # Repair product Serial A1
            with ro_form.operations.new() as operation:
                operation.type = 'remove'
                operation.product_id = product_to_remove
                operation.lot_id = ptremove_lot  # Remove product Serial B2 from the product
            ro = ro_form.save()
        ro.action_validate()
        ro.action_repair_start()
        ro.action_repair_end()

        # Create a manufacturing order with product (with SN A2)
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = product_to_repair
        with mo2_form.move_raw_ids.new() as move:
            move.product_id = product_to_remove
            move.product_uom_qty = 1
            move.move_line_ids.lot_id = ptremove_lot  # Set component serial to B2 again, it is possible
        mo2 = mo2_form.save()
        mo2.action_confirm()
        # Set serial to A2
        mo2.lot_producing_id = self.env['stock.production.lot'].create({
            'name': 'A2',
            'product_id': product_to_repair.id,
            'company_id': self.env.user.company_id.id
        })
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
            action = mo.button_mark_done()
            wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
            wizard.process()
            return mo

        stock_location = self.env.ref('stock.stock_location_stock')

        finished, component = self.env['product.product'].create([{
            'name': 'Finished Product',
            'type': 'product',
        }, {
            'name': 'SN Componentt',
            'type': 'product',
            'tracking': 'serial',
        }])

        sn_lot = self.env['stock.production.lot'].create({
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
        with ro_form.operations.new() as ro_line:
            ro_line.type = 'remove'
            ro_line.product_id = component
            ro_line.lot_id = sn_lot
            ro_line.location_dest_id = stock_location
        ro = ro_form.save()
        ro.action_validate()
        ro.action_repair_start()
        ro.action_repair_end()

        mo = produce_one(finished, component)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_raw_ids.lot_ids, sn_lot)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon

from odoo.tests import tagged
from dateutil.relativedelta import relativedelta


@tagged('post_install', '-at_install')
class TestSubcontractingBasic(TransactionCase):
    def test_subcontracting_location_1(self):
        """ Checks the creation and presence of the subcontracting location. """
        self.assertTrue(self.env.company.subcontracting_location_id)
        self.assertTrue(self.env.company.subcontracting_location_id.active)
        company2 = self.env['res.company'].create({'name': 'Test Company'})
        self.assertTrue(company2.subcontracting_location_id)
        self.assertTrue(self.env.company.subcontracting_location_id != company2.subcontracting_location_id)


@tagged('post_install', '-at_install')
class TestSubcontractingFlows(TestMrpSubcontractingCommon):
    def test_flow_1(self):
        """ Don't tick any route on the components and trigger the creation of the subcontracting
        manufacturing order through a receipt picking. Create a reordering rule in the
        subcontracting locations for a component and run the scheduler to resupply. Checks if the
        resupplying actually works
        """
        # Check subcontracting picking Type
        self.assertTrue(all(self.env['stock.warehouse'].search([]).with_context(active_test=False).mapped('subcontracting_type_id.use_create_components_lots')))
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # Nothing should be tracked
        self.assertTrue(all(m.product_uom_qty == m.reserved_availability for m in picking_receipt.move_ids))
        self.assertEqual(picking_receipt.state, 'assigned')
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo), 1)
        self.assertEqual(len(mo.picking_ids), 0)
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEqual(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # Create a RR
        pg1 = self.env['procurement.group'].create({})
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'xxx',
            'product_id': self.comp1.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
            'location_id': self.env.user.company_id.subcontracting_location_id.id,
            'group_id': pg1.id,
        })

        # Run the scheduler and check the created picking
        self.env['procurement.group'].run_scheduler()
        picking = self.env['stock.picking'].search([('group_id', '=', pg1.id)])
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.picking_type_id, wh.subcontracting_resupply_type_id)
        picking_receipt.move_ids.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -1)
        self.assertEqual(avail_qty_comp2, -1)
        self.assertEqual(avail_qty_finished, 1)

        # Ensure returns to subcontractor location
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=picking_receipt.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_picking_id, pick_type_id = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_picking_id)
        self.assertEqual(len(return_picking), 1)
        self.assertEqual(return_picking.move_ids.location_dest_id, self.subcontractor_partner1.property_stock_subcontractor)

    def test_flow_2(self):
        """ Tick "Resupply Subcontractor on Order" on the components and trigger the creation of
        the subcontracting manufacturing order through a receipt picking. Checks if the resupplying
        actually works. Also set a different subcontracting location on the partner.
        """
        # Tick "resupply subconractor on order"
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(4, resupply_sub_on_order_route.id, None)]})
        # Create a different subcontract location & check rules replication
        reference_location_rules_count = self.env['stock.rule'].search_count(['|', ('location_src_id', '=', self.env.company.subcontracting_location_id.id), ('location_dest_id', '=', self.env.company.subcontracting_location_id.id)])
        partner_subcontract_location = self.env['stock.location'].create({
            'name': 'Specific partner location',
            'location_id': self.env.ref('stock.stock_location_locations_partner').id,
            'usage': 'internal',
            'company_id': self.env.company.id,
            'is_subcontracting_location': True,
        })
        custom_location_rules_count = self.env['stock.rule'].search_count(['|', ('location_src_id', '=', partner_subcontract_location.id), ('location_dest_id', '=', partner_subcontract_location.id)])
        self.assertEqual(reference_location_rules_count, custom_location_rules_count)
        self.subcontractor_partner1.property_stock_subcontractor = partner_subcontract_location.id
        # Add a manufacturing lead time to check that the resupply delivery is correctly planned 2 days
        # before the subcontracting receipt
        self.finished.produce_delay = 2

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # Nothing should be tracked
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        # Pickings should directly be created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo.picking_ids), 1)
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.picking_ids.move_ids), 2)

        picking = mo.picking_ids
        wh = picking.picking_type_id.warehouse_id

        # The picking should be a delivery order
        self.assertEqual(picking.picking_type_id, wh.subcontracting_resupply_type_id)
        # The date planned should be correct
        self.assertEqual(picking_receipt.scheduled_date, picking.scheduled_date + relativedelta(days=self.finished.produce_delay))

        self.assertEqual(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # No manufacturing order for `self.comp2`
        comp2mo = self.env['mrp.production'].search([('bom_id', '=', self.comp2_bom.id)])
        self.assertEqual(len(comp2mo), 0)

        picking_receipt.move_ids.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -1)
        self.assertEqual(avail_qty_comp2, -1)
        self.assertEqual(avail_qty_finished, 1)

        avail_qty_comp1_in_global_location = self.env['stock.quant']._get_available_quantity(self.comp1, self.env.company.subcontracting_location_id, allow_negative=True)
        avail_qty_comp2_in_global_location = self.env['stock.quant']._get_available_quantity(self.comp2, self.env.company.subcontracting_location_id, allow_negative=True)
        self.assertEqual(avail_qty_comp1_in_global_location, 0.0)
        self.assertEqual(avail_qty_comp2_in_global_location, 0.0)

    def test_flow_3(self):
        """ Tick "Resupply Subcontractor on Order" and "MTO" on the components and trigger the
        creation of the subcontracting manufacturing order through a receipt picking. Checks if the
        resupplying actually works. One of the component has also "manufacture" set and a BOM
        linked. Checks that an MO is created for this one.
        """
        # Tick "resupply subconractor on order"
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(6, None, [resupply_sub_on_order_route.id])]})

        # Tick "manufacture" and MTO on self.comp2
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')])
        self.comp2.write({'route_ids': [(4, manufacture_route.id, None)]})
        self.comp2.write({'route_ids': [(4, mto_route.id, None)]})

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # Nothing should be tracked
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        # Pickings should directly be created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(mo.state, 'confirmed')

        picking_delivery = mo.picking_ids
        self.assertEqual(len(picking_delivery), 1)
        self.assertEqual(len(picking_delivery.move_ids), 2)
        self.assertEqual(picking_delivery.origin, picking_receipt.name)
        self.assertEqual(picking_delivery.partner_id, picking_receipt.partner_id)

        # The picking should be a delivery order
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEqual(mo.picking_ids.picking_type_id, wh.subcontracting_resupply_type_id)

        self.assertEqual(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # As well as a manufacturing order for `self.comp2`
        comp2mo = self.env['mrp.production'].search([('bom_id', '=', self.comp2_bom.id)])
        self.assertEqual(len(comp2mo), 1)
        picking_receipt.move_ids.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -1)
        self.assertEqual(avail_qty_comp2, -1)
        self.assertEqual(avail_qty_finished, 1)

    def test_flow_4(self):
        """ Tick "Manufacture" and "MTO" on the components and trigger the
        creation of the subcontracting manufacturing order through a receipt
        picking. Checks that the delivery and MO for its components are
        automatically created.
        """
        # Required for `location_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        # Tick "manufacture" and MTO on self.comp2
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')])
        self.comp2.write({'route_ids': [(6, None, [manufacture_route.id, mto_route.id])]})

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.comp2
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 10.0
        orderpoint_form.location_id = self.env.company.subcontracting_location_id
        orderpoint = orderpoint_form.save()

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        warehouse = picking_receipt.picking_type_id.warehouse_id

        # Pickings should directly be created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(mo.state, 'confirmed')

        picking_delivery = mo.picking_ids
        self.assertFalse(picking_delivery)

        picking_delivery = self.env['stock.picking'].search([('origin', 'ilike', '%' + picking_receipt.name + '%')])
        self.assertFalse(picking_delivery)

        move = self.env['stock.move'].search([
            ('product_id', '=', self.comp2.id),
            ('location_id', '=', warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.env.company.subcontracting_location_id.id)
        ])
        self.assertTrue(move)
        picking_delivery = move.picking_id
        self.assertTrue(picking_delivery)
        self.assertEqual(move.product_uom_qty, 11.0)

        # As well as a manufacturing order for `self.comp2`
        comp2mo = self.env['mrp.production'].search([('bom_id', '=', self.comp2_bom.id)])
        self.assertEqual(len(comp2mo), 1)

    def test_flow_5(self):
        """ Check that the correct BoM is chosen accordingly to the partner
        """
        # We create a second partner of type subcontractor
        main_partner_2 = self.env['res.partner'].create({'name': 'main_partner'})
        subcontractor_partner2 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'parent_id': main_partner_2.id,
            'company_id': self.env.ref('base.main_company').id
        })

        # We create a different BoM for the same product
        comp3 = self.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.product_tmpl_id = self.finished.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp1
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = comp3
            bom_line.product_qty = 1
        bom2 = bom_form.save()

        # We assign the second BoM to the new partner
        self.bom.write({'subcontractor_ids': [(4, self.subcontractor_partner1.id, None)]})
        bom2.write({'subcontractor_ids': [(4, subcontractor_partner2.id, None)]})

        # Create a receipt picking from the subcontractor1
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt1 = picking_form.save()
        picking_receipt1.action_confirm()

        # Create a receipt picking from the subcontractor2
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = subcontractor_partner2
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt2 = picking_form.save()
        picking_receipt2.action_confirm()

        mo_pick1 = picking_receipt1.move_ids.mapped('move_orig_ids.production_id')
        mo_pick2 = picking_receipt2.move_ids.mapped('move_orig_ids.production_id')
        self.assertEqual(len(mo_pick1), 1)
        self.assertEqual(len(mo_pick2), 1)
        self.assertEqual(mo_pick1.bom_id, self.bom)
        self.assertEqual(mo_pick2.bom_id, bom2)

    def test_flow_6(self):
        """ Extra quantity on the move.
        """
        # We create a second partner of type subcontractor
        main_partner_2 = self.env['res.partner'].create({'name': 'main_partner'})
        subcontractor_partner2 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'parent_id': main_partner_2.id,
            'company_id': self.env.ref('base.main_company').id,
        })
        self.env.invalidate_all()

        # We create a different BoM for the same product
        comp3 = self.env['product.product'].create({
            'name': 'Component3',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.product_tmpl_id = self.finished.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp1
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = comp3
            bom_line.product_qty = 2
        bom2 = bom_form.save()

        # We assign the second BoM to the new partner
        self.bom.write({'subcontractor_ids': [(4, self.subcontractor_partner1.id, None)]})
        bom2.write({'subcontractor_ids': [(4, subcontractor_partner2.id, None)]})

        # Create a receipt picking from the subcontractor1
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = subcontractor_partner2
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        picking_receipt.move_ids.quantity_done = 3.0
        picking_receipt._action_done()
        mo = picking_receipt._get_subcontract_production()
        move_comp1 = mo.move_raw_ids.filtered(lambda m: m.product_id == self.comp1)
        move_comp3 = mo.move_raw_ids.filtered(lambda m: m.product_id == comp3)
        self.assertEqual(sum(move_comp1.mapped('product_uom_qty')), 3.0)
        self.assertEqual(sum(move_comp3.mapped('product_uom_qty')), 6.0)
        self.assertEqual(sum(move_comp1.mapped('quantity_done')), 3.0)
        self.assertEqual(sum(move_comp3.mapped('quantity_done')), 6.0)
        move_finished = mo.move_finished_ids
        self.assertEqual(sum(move_finished.mapped('product_uom_qty')), 3.0)
        self.assertEqual(sum(move_finished.mapped('quantity_done')), 3.0)

    def test_flow_8(self):
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(4, resupply_sub_on_order_route.id, None)]})

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 5
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        picking_receipt.move_ids.quantity_done = 3
        backorder_wiz = picking_receipt.button_validate()
        backorder_wiz = Form(self.env[backorder_wiz['res_model']].with_context(backorder_wiz['context'])).save()
        backorder_wiz.process()

        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_receipt.id)])
        self.assertTrue(backorder)
        self.assertEqual(backorder.move_ids.product_uom_qty, 2)
        mo_done = backorder.move_ids.move_orig_ids.production_id.filtered(lambda p: p.state == 'done')
        backorder_mo = backorder.move_ids.move_orig_ids.production_id.filtered(lambda p: p.state != 'done')
        self.assertTrue(mo_done)
        self.assertEqual(mo_done.qty_produced, 3)
        self.assertEqual(mo_done.product_uom_qty, 3)
        self.assertTrue(backorder_mo)
        self.assertEqual(backorder_mo.product_uom_qty, 2)
        self.assertEqual(backorder_mo.qty_produced, 0)
        backorder.move_ids.quantity_done = 2
        backorder._action_done()
        self.assertTrue(picking_receipt.move_ids.move_orig_ids[0].production_id.state == 'done')

    def test_flow_9(self):
        """Ensure that cancel the subcontract moves will also delete the
        components need for the subcontractor.
        """
        resupply_sub_on_order_route = self.env['stock.route'].search([
            ('name', '=', 'Resupply Subcontractor on Order')
        ])
        (self.comp1 + self.comp2).write({
            'route_ids': [(4, resupply_sub_on_order_route.id)]
        })

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 5
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        picking_delivery = self.env['stock.move'].search([
            ('product_id', 'in', (self.comp1 | self.comp2).ids)
        ]).picking_id
        self.assertTrue(picking_delivery)
        self.assertEqual(picking_delivery.state, 'confirmed')
        self.assertEqual(self.comp1.virtual_available, -5)
        self.assertEqual(self.comp2.virtual_available, -5)
        # action_cancel is not call on the picking in order
        # to test behavior from other source than picking (e.g. puchase).
        picking_receipt.move_ids._action_cancel()
        self.assertEqual(picking_delivery.state, 'cancel')
        self.assertEqual(self.comp1.virtual_available, 0.0)
        self.assertEqual(self.comp1.virtual_available, 0.0)

    def test_flow_10(self):
        """Receipts from a children contact of a subcontractor are properly
        handled.
        """
        # Create a children contact
        subcontractor_contact = self.env['res.partner'].create({
            'name': 'Test children subcontractor contact',
            'parent_id': self.subcontractor_partner1.id,
        })
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = subcontractor_contact
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        # Check that a manufacturing order is created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo), 1)

    def test_flow_flexible_bom_1(self):
        """ Record Component for a bom subcontracted with a flexible and flexible + warning consumption """
        self.bom.consumption = 'flexible'
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        self.assertEqual(picking_receipt.display_action_record_components, 'facultative')
        action = picking_receipt.action_record_components()
        mo = self.env['mrp.production'].browse(action['res_id'])
        mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
        mo_form.qty_producing = 1
        with mo_form.move_line_raw_ids.edit(0) as ml:
            self.assertEqual(ml.product_id, self.comp1)
            self.assertEqual(ml.qty_done, 1)
            ml.qty_done = 2
        mo = mo_form.save()
        mo.subcontracting_record_component()
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.qty_done, 2)

        # We should not be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        self.assertEqual(avail_qty_comp1, -2)

    def test_flow_warning_bom_1(self):
        """ Record Component for a bom subcontracted with a flexible and flexible + warning consumption """
        self.bom.consumption = 'warning'
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 2
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        self.assertEqual(picking_receipt.display_action_record_components, 'facultative')
        action = picking_receipt.action_record_components()
        mo = self.env['mrp.production'].browse(action['res_id'])
        mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
        mo_form.qty_producing = 1
        with mo_form.move_line_raw_ids.edit(0) as ml:
            self.assertEqual(ml.product_id, self.comp1)
            self.assertEqual(ml.qty_done, 1)
            ml.qty_done = 2
        mo = mo_form.save()
        action_warning = mo.subcontracting_record_component()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action_warning['context']))
        warning = warning.save()
        warning.action_cancel()

        action_warning = mo.subcontracting_record_component()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action_warning['context']))
        warning = warning.save()
        action = warning.action_confirm()

        self.assertEqual(mo.move_raw_ids[0].move_line_ids.qty_done, 2)

        # Record another over-consumption for the remaining components
        mo_2 = self.env['mrp.production'].browse(action['res_id'])
        with Form(mo_2.with_context(**action['context']), view=action['view_id']) as mo_form:
            mo_form.qty_producing = 1
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1)
                self.assertEqual(ml.qty_done, 1)
                ml.qty_done = 3
            mo_2 = mo_form.save()

        action_warning_2 = mo_2.subcontracting_record_component()
        self.assertEqual(action_warning_2.get('res_model'), 'mrp.consumption.warning')
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action_warning_2['context']))
        warning = warning.save()
        warning.action_confirm()

        self.assertEqual(mo_2.move_raw_ids[0].move_line_ids.qty_done, 3)

        # We should not be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        self.assertEqual(avail_qty_comp1, -5)

    def test_flow_warning_bom_2(self):
        """ For an initial demand of 10 subcontracted products
            - The production of 3 is recorded, with an over-consumption of its components
            After the picking is validated, check that the over-consumption stays as-is.
        """
        self.bom.consumption = 'warning'
        # Create reception picking
        with Form(self.env['stock.picking']) as picking_form:
            picking_form.picking_type_id = self.warehouse.in_type_id
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.product_uom_qty = 10
            receipt = picking_form.save()
        receipt.action_confirm()

        # Record the over-consumption of a component
        self.assertTrue(receipt._get_subcontract_production())
        action_record = receipt.action_record_components()
        sbc_mo = self.env['mrp.production'].browse(action_record['res_id'])
        with Form(sbc_mo.with_context(**action_record['context']), view=action_record['view_id']) as mo_form:
            mo_form.qty_producing = 3
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1)
                self.assertEqual(ml.qty_done, 3)
                ml.qty_done = 5
            sbc_mo = mo_form.save()
        # Confirm the over-consumption through the warning
        action_warning = sbc_mo.subcontracting_record_component()
        wizard_warning = Form(self.env['mrp.consumption.warning'].with_context(**action_warning['context'])).save()
        wizard_warning.action_confirm()

        self.assertEqual(sbc_mo.move_raw_ids[0].move_line_ids.qty_done, 5)

        # Validate the picking without backorders
        action_backorder = receipt.button_validate()
        wizard_backorder = Form(self.env[action_backorder['res_model']].with_context(action_backorder['context'])).save()
        wizard_backorder.process_cancel_backorder()

        # Check that the over-consumption is still present
        self.assertEqual(sbc_mo.move_raw_ids[0].move_line_ids.qty_done, 5)

    def test_mrp_report_bom_structure_subcontracting(self):
        self.comp2_bom.write({'type': 'subcontract', 'subcontractor_ids': [Command.link(self.subcontractor_partner1.id)]})
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 10,
        })
        supplier = self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 5,
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 1,
            'min_qty': 5,
        })
        self.assertTrue(supplier.is_subcontractor)
        self.comp1.standard_price = 5
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, searchQty=1, searchVariant=False)
        subcontracting_values = report_values['lines']['subcontracting']
        self.assertEqual(subcontracting_values['name'], self.subcontractor_partner1.display_name)
        self.assertEqual(report_values['lines']['bom_cost'], 20)  # 10 For subcontracting + 5 for comp1 + 5 for subcontracting of comp2_bom
        self.assertEqual(subcontracting_values['bom_cost'], 10)
        self.assertEqual(subcontracting_values['prod_cost'], 10)
        self.assertEqual(report_values['lines']['components'][0]['bom_cost'], 5)
        self.assertEqual(report_values['lines']['components'][1]['bom_cost'], 5)
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, searchQty=3, searchVariant=False)
        subcontracting_values = report_values['lines']['subcontracting']
        self.assertEqual(report_values['lines']['bom_cost'], 60)  # 30 for subcontracting + 15 for comp1 + 15 for subcontracting of comp2_bom
        self.assertEqual(subcontracting_values['bom_cost'], 30)
        self.assertEqual(subcontracting_values['prod_cost'], 30)
        self.assertEqual(report_values['lines']['components'][0]['bom_cost'], 15)
        self.assertEqual(report_values['lines']['components'][1]['bom_cost'], 15)
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, searchQty=5, searchVariant=False)
        subcontracting_values = report_values['lines']['subcontracting']
        self.assertEqual(report_values['lines']['bom_cost'], 80)  # 50 for subcontracting + 25 for comp1 + 5 for subcontracting of comp2_bom
        self.assertEqual(subcontracting_values['bom_cost'], 50)
        self.assertEqual(subcontracting_values['prod_cost'], 50)
        self.assertEqual(report_values['lines']['components'][0]['bom_cost'], 25)
        self.assertEqual(report_values['lines']['components'][1]['bom_cost'], 5)

    def test_several_backorders(self):
        def process_picking(picking, qty):
            picking.move_ids.quantity_done = qty
            action = picking.button_validate()
            if isinstance(action, dict):
                wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
                wizard.process()

        resupply_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        finished, component = self.env['product.product'].create([{
            'name': 'Finished Product',
            'type': 'product',
        }, {
            'name': 'Component',
            'type': 'product',
            'route_ids': [(4, resupply_route.id)],
        }])

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [(4, self.subcontractor_partner1.id)],
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})],
        })

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = finished
            move.product_uom_qty = 5
        picking = picking_form.save()
        picking.action_confirm()

        supply_picking = self.env['mrp.production'].search([('bom_id', '=', bom.id)]).picking_ids
        process_picking(supply_picking, 5)

        process_picking(picking, 1.25)

        backorder01 = picking.backorder_ids
        process_picking(backorder01, 1)

        backorder02 = backorder01.backorder_ids
        process_picking(backorder02, 0)
        self.assertEqual(backorder02.move_ids.quantity_done, 2.75)

        self.assertEqual(self.env['mrp.production'].search_count([('bom_id', '=', bom.id)]), 3)

    def test_several_backorders_2(self):
        # This test ensure that the backorders finished moves are correctly made (Production -> Subcontracting -> Stock)
        # When the receipt is done, the Subcontracting location should have 0 quantity of the finished product.
        # In more detail, this test checks that everything is done correctly
        # when the quantity of the backorder is set on the stock.move.line instead of the stock.move,
        # it can for example happens if the finished product is tracked by Serial Number.

        def process_picking_with_backorder(picking, qty):
            # Process the picking by putting the given quantity on the stock.move.line
            picking.move_line_ids.ensure_one().qty_done = qty
            action = picking.button_validate()
            if isinstance(action, dict):
                wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
                wizard.process()
            return picking.backorder_ids

        def check_quants(product, stock_qty, sub_qty, prod_qty):
            # Check the quantities of the Stock, Subcontracting and Production locations for the given product
            subcontracting_location = self.env.company.subcontracting_location_id
            production_location = product.property_stock_production
            stock_location = self.env.ref('stock.stock_location_stock')

            self.assertEqual(sub_qty, self.env['stock.quant']._gather(product, subcontracting_location).quantity)
            self.assertEqual(stock_qty, self.env['stock.quant']._gather(product, stock_location).quantity)
            self.assertEqual(prod_qty, self.env['stock.quant']._gather(product, production_location).quantity)

        in_pck_type = self.env.ref('stock.picking_type_in')
        in_pck_type.write({'show_operations': True, 'show_reserved': True})

        finished = self.env['product.product'].create({'name': 'Finished Product', 'type': 'product'})
        component = self.env['product.product'].create([{'name': 'Component', 'type': 'product'}])
        self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [(4, self.subcontractor_partner1.id)],
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})],
        })

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = in_pck_type
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = finished
            move.product_uom_qty = 6
        picking = picking_form.save()
        picking.action_confirm()

        backorder01 = process_picking_with_backorder(picking, 1)
        check_quants(product=finished, stock_qty=1, sub_qty=0, prod_qty=-1)
        check_quants(product=component, stock_qty=0, sub_qty=-1, prod_qty=1)

        backorder02 = process_picking_with_backorder(backorder01, 2)
        check_quants(product=finished, stock_qty=3, sub_qty=0, prod_qty=-3)
        check_quants(product=component, stock_qty=0, sub_qty=-3, prod_qty=3)

        process_picking_with_backorder(backorder02, 3)
        check_quants(product=finished, stock_qty=6, sub_qty=0, prod_qty=-6)
        check_quants(product=component, stock_qty=0, sub_qty=-6, prod_qty=6)

    def test_subcontracting_rules_replication(self):
        """ Test activate/archive subcontracting location rules."""
        reference_location_rules = self.env['stock.rule'].search(['|', ('location_src_id', '=', self.env.company.subcontracting_location_id.id), ('location_dest_id', '=', self.env.company.subcontracting_location_id.id)])
        warehouse_related_rules = reference_location_rules.filtered(lambda r: r.warehouse_id)
        company_rules = reference_location_rules - warehouse_related_rules
        # Create a custom subcontracting location
        custom_subcontracting_location = self.env['stock.location'].create({
            'name': 'Custom Subcontracting Location',
            'location_id': self.env.ref('stock.stock_location_locations').id,
            'usage': 'internal',
            'company_id': self.env.company.id,
            'is_subcontracting_location': True,
        })
        custom_location_rules_count = self.env['stock.rule'].search_count(['|', ('location_src_id', '=', custom_subcontracting_location.id), ('location_dest_id', '=', custom_subcontracting_location.id)])
        self.assertEqual(len(reference_location_rules), custom_location_rules_count)
        # Add a new warehouse
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Additional Warehouse',
            'code': 'ADD'
        })
        company_subcontracting_locations_rules_count = self.env['stock.rule'].search_count(['&', ('company_id', '=', warehouse.company_id.id), '|', ('location_src_id.is_subcontracting_location', '=', 'True'), ('location_dest_id.is_subcontracting_location', '=', 'True')])
        self.assertEqual(len(warehouse_related_rules) * 4 + len(company_rules) * 2, company_subcontracting_locations_rules_count)
        # Custom location no longer a subcontracting one
        custom_subcontracting_location.is_subcontracting_location = False
        custom_location_rules_count = self.env['stock.rule'].search_count(['|', ('location_src_id', '=', custom_subcontracting_location.id), ('location_dest_id', '=', custom_subcontracting_location.id)])
        self.assertEqual(custom_location_rules_count, 0)

    def test_subcontracting_date_warning(self):
        with Form(self.env['stock.picking'].with_context(default_immediate_transfer=True)) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.quantity_done = 3
            picking_receipt = picking_form.save()
        self.assertEqual(picking_form.json_popover, False)

        subcontract = picking_receipt._get_subcontract_production()
        self.assertEqual(subcontract.date_planned_start, picking_receipt.scheduled_date)
        self.assertEqual(subcontract.date_planned_finished, picking_receipt.scheduled_date)

    def test_subcontracting_set_quantity_done(self):
        """ Tests to set a quantity done directly on a subcontracted move without using the subcontracting wizard. Checks that it does the same
            as it would do with the wizard. Since immediate/planned transfers have different flows, we need to test both.
        """
        self.bom.consumption = 'flexible'
        quantities = [10, 15, 12, 14]

        # For planned transfers, as some triggers are different if it's an immediate transfer.
        with Form(self.env['stock.picking']) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.product_uom_qty = quantities[0]
            picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        self.assertEqual(picking_receipt.immediate_transfer, False)
        move = picking_receipt.move_ids_without_package

        for qty in quantities[1:]:
            move.quantity_done = qty
            subcontracted = move._get_subcontract_production().filtered(lambda p: p.state != 'cancel')
            self.assertEqual(sum(subcontracted.mapped('product_qty')), qty)
            self.assertEqual(move.product_uom_qty, quantities[0])

        picking_receipt.button_validate()
        self.assertEqual(move.product_uom_qty, quantities[-1])
        self.assertEqual(move.quantity_done, quantities[-1])
        subcontracted = move._get_subcontract_production().filtered(lambda p: p.state == 'done')
        self.assertEqual(sum(subcontracted.mapped('qty_produced')), quantities[-1])

        # Now the same with an immediate transfer
        with Form(self.env['stock.picking'].with_context(default_immediate_transfer=True)) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.quantity_done = quantities[0]
            picking_receipt = picking_form.save()
        self.assertEqual(picking_receipt.immediate_transfer, True)
        move = picking_receipt.move_ids_without_package

        subcontracted = move._get_subcontract_production()
        self.assertEqual(subcontracted.product_qty, quantities[0])

        for qty in quantities[1:]:
            move.quantity_done = qty
            subcontracted = move._get_subcontract_production().filtered(lambda p: p.state != 'cancel')
            self.assertEqual(sum(subcontracted.mapped('product_qty')), qty)
            self.assertEqual(move.product_uom_qty, qty)

        picking_receipt.button_validate()
        self.assertEqual(move.product_uom_qty, quantities[-1])
        self.assertEqual(move.quantity_done, quantities[-1])
        subcontracted = move._get_subcontract_production().filtered(lambda p: p.state == 'done')
        self.assertEqual(sum(subcontracted.mapped('qty_produced')), quantities[-1])

    def test_change_reception_serial(self):
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('stock.group_production_lot').id)]})
        self.finished.tracking = 'serial'
        self.bom.consumption = 'flexible'

        finished_lots = self.env['stock.lot'].create([{
            'name': 'lot_%s' % number,
            'product_id': self.finished.id,
            'company_id': self.env.company.id,
        } for number in range(3)])

        with Form(self.env['stock.picking']) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.product_uom_qty = 3
            picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # Register serial number for each finished product
        for lot in finished_lots:
            action = picking_receipt.move_ids.action_show_details()
            self.assertEqual(action['name'], 'Subcontract', "It should open the subcontract record components wizard instead.")
            mo = self.env['mrp.production'].browse(action['res_id'])
            with Form(mo.with_context(action['context']), view=action['view_id']) as mo_form:
                mo_form.qty_producing = 1
                mo_form.lot_producing_id = lot
                mo_form.save()
            mo.subcontracting_record_component()

        subcontract_move = picking_receipt.move_ids_without_package.filtered(lambda m: m.is_subcontract)
        self.assertEqual(len(subcontract_move._get_subcontract_production()), 3)
        self.assertEqual(len(subcontract_move._get_subcontract_production().lot_producing_id), 3)
        self.assertRecordValues(subcontract_move._get_subcontract_production().lot_producing_id.sorted('id'), [
            {'id': finished_lots[0].id},
            {'id': finished_lots[1].id},
            {'id': finished_lots[2].id},
        ])

        new_lot = self.env['stock.lot'].create({
            'name': 'lot_alter',
            'product_id': self.finished.id,
            'company_id': self.env.company.id,
        })
        action = picking_receipt.move_ids.action_show_details()
        self.assertEqual(action['name'], 'Detailed Operations', "The subcontract record components wizard shouldn't be available now.")
        with Form(subcontract_move.with_context(action['context']), view=action['view_id']) as move_form:
            with move_form.move_line_nosuggest_ids.edit(2) as move_line:
                move_line.lot_id = new_lot
            move_form.save()

        subcontracted_mo = subcontract_move._get_subcontract_production()
        self.assertEqual(len(subcontracted_mo.filtered(lambda p: p.lot_producing_id == new_lot)), 1)
        self.assertEqual(len(subcontracted_mo.filtered(lambda p: p.lot_producing_id != new_lot)), 2)

    def test_multiple_component_records_for_incomplete_move(self):
        self.bom.consumption = 'flexible'
        with Form(self.env['stock.picking']) as picking_form:
            picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
            picking_form.partner_id = self.subcontractor_partner1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.finished
                move.product_uom_qty = 10
            picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        move = picking_receipt.move_ids_without_package

        # Register the five first finished products
        action = move.action_show_details()
        mo = self.env['mrp.production'].browse(action['res_id'])
        with Form(mo.with_context(action['context']), view=action['view_id']) as mo_form:
            mo_form.qty_producing = 5
            mo_form.save()
        mo.subcontracting_record_component()
        self.assertEqual(move.quantity_done, 5)

        # Register two other finished products
        action = move.action_show_details()
        mo = self.env['mrp.production'].browse(action['res_id'])
        with Form(mo.with_context(action['context']), view=action['view_id']) as mo_form:
            mo_form.qty_producing = 2
            mo_form.save()
        mo.subcontracting_record_component()
        self.assertEqual(move.quantity_done, 7)

        # Check MO state before validating without backorder
        action = move.action_show_details()
        mo = self.env['mrp.production'].browse(action['res_id'])
        self.assertEqual(mo.state, 'to_close')

        # Validate picking without backorder
        backorder_wizard_dict = picking_receipt.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process_cancel_backorder()

        self.assertEqual(mo.product_qty, 3)
        self.assertEqual(mo.state, 'cancel')
        self.assertRecordValues(move._get_subcontract_production(), [
            {'product_qty': 5, 'state': 'done'},
            {'product_qty': 2, 'state': 'done'},
            {'product_qty': 3, 'state': 'cancel'},
        ])

    def test_decrease_quantity_done(self):
        self.bom.consumption = 'flexible'
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        uom_duo = self.env['uom.uom'].create({
            'category_id': self.finished.uom_id.category_id.id,
            'name': 'Duos',
            'uom_type': 'bigger',
            'factor_inv': 2.0,
        })

        receipt = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner1.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_uom_qty': 10.0,
                'product_uom': uom_duo.id,
                'location_id': supplier_location.id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })],
        })

        receipt.action_confirm()
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertRecordValues(productions, [
            {'qty_producing': 0.0, 'product_qty': 10.0, 'state': 'confirmed'},
        ])

        receipt.move_ids.quantity_done = 6
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertEqual(receipt.move_ids.product_uom_qty, 10.0, 'Demand should not be impacted')
        self.assertRecordValues(productions, [
            {'qty_producing': 6.0, 'product_qty': 6.0, 'state': 'to_close'},
            {'qty_producing': 4.0, 'product_qty': 4.0, 'state': 'to_close'},
        ])

        receipt.move_ids.quantity_done = 9
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertEqual(receipt.move_ids.product_uom_qty, 10.0, 'Demand should not be impacted')
        self.assertRecordValues(productions, [
            {'qty_producing': 6.0, 'product_qty': 6.0, 'state': 'to_close'},
            {'qty_producing': 3.0, 'product_qty': 3.0, 'state': 'to_close'},
            {'qty_producing': 1.0, 'product_qty': 1.0, 'state': 'to_close'},
        ])

        receipt.move_ids.quantity_done = 7
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertEqual(receipt.move_ids.product_uom_qty, 10.0, 'Demand should not be impacted')
        self.assertRecordValues(productions, [
            {'qty_producing': 6.0, 'product_qty': 6.0, 'state': 'to_close'},
            {'qty_producing': 1.0, 'product_qty': 1.0, 'state': 'to_close'},
            {'qty_producing': 3.0, 'product_qty': 3.0, 'state': 'to_close'},
        ])

        receipt.move_ids.quantity_done = 4
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertEqual(receipt.move_ids.product_uom_qty, 10.0, 'Demand should not be impacted')
        self.assertRecordValues(productions, [
            {'qty_producing': 4.0, 'product_qty': 4.0, 'state': 'to_close'},
            {'qty_producing': 1.0, 'product_qty': 1.0, 'state': 'cancel'},
            {'qty_producing': 6.0, 'product_qty': 6.0, 'state': 'to_close'},
        ])

        receipt.move_ids.quantity_done = 0
        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertEqual(receipt.move_ids.product_uom_qty, 10.0, 'Demand should not be impacted')
        self.assertRecordValues(productions, [
            {'qty_producing': 4.0, 'product_qty': 4.0, 'state': 'cancel'},
            {'qty_producing': 1.0, 'product_qty': 1.0, 'state': 'cancel'},
            {'qty_producing': 10.0, 'product_qty': 10.0, 'state': 'to_close'},
        ])

    def test_validate_partial_subcontracting_without_backorder(self):
        """ Test the validation of a partial subcontracting without creating a backorder."""
        self.bom.consumption = 'flexible'
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        receipt = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner1.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [Command.create({
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_uom_qty': 20.0,
                'location_id': supplier_location.id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })],
        })
        receipt.action_confirm()
        self.assertEqual(receipt.state, 'assigned')
        receipt.move_ids.quantity_done = 19.8
        # Validate picking without backorder
        backorder_wizard_dict = receipt.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process_cancel_backorder()
        self.assertEqual(receipt.state, 'done')
        productions = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)]).sorted('id')
        self.assertRecordValues(productions, [
            {'product_qty': 19.8, 'qty_producing': 19.8, 'state': 'done'},
            {'product_qty': 0.2, 'qty_producing': 0.2, 'state': 'cancel'},
        ])

    def test_strict_consumption_backorders(self):
        """ Test for the correct consumption of components with a 'strict' consumption BoM and available quantity
            of the component in the subcontracting location.
        """

        def validate_receipt_with_backorder(picking, qty):
            picking.move_ids.quantity_done = qty
            action_dict = picking.button_validate()
            backorder_wizard = Form(self.env[action_dict['res_model']].with_context(action_dict['context']))
            backorder_wizard.save().process()
            return picking.backorder_ids

        self.bom.consumption = 'strict'
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        subcontract_location = self.subcontractor_partner1.property_stock_subcontractor
        self.env['stock.quant']._update_available_quantity(self.comp1, subcontract_location, 9)

        receipt = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner1.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [
                Command.create({
                    'name': self.finished.name,
                    'product_id': self.finished.id,
                    'product_uom_qty': 9,
                    'product_uom': self.finished.uom_id.id,
                    'location_id': supplier_location.id,
                    'location_dest_id': self.warehouse.lot_stock_id.id,
                })
            ],
        })

        receipt.action_confirm()
        backorder_1 = validate_receipt_with_backorder(receipt, 3)
        _ = validate_receipt_with_backorder(backorder_1, 3)

        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        self.assertRecordValues(productions, [
            {'qty_producing': 3.0, 'product_qty': 3.0, 'state': 'done'},
            {'qty_producing': 3.0, 'product_qty': 3.0, 'state': 'done'},
            {'qty_producing': 0.0, 'product_qty': 3.0, 'state': 'progress'},
        ])

        comp1_moves = productions.move_raw_ids.filtered(lambda m: m.product_id == self.comp1)
        self.assertRecordValues(comp1_moves, [
            {'quantity_done': 3.0, 'product_qty': 3.0, 'state': 'done'},
            {'quantity_done': 3.0, 'product_qty': 3.0, 'state': 'done'},
            {'quantity_done': 3.0, 'product_qty': 3.0, 'state': 'assigned'},
        ])

    def test_strict_consumption_backorders_serial(self):
        """ Test for the correct consumption of components with a 'strict' consumption BoM and available quantity
            of the component in the subcontracting location and serial tracking.
        """

        self.finished.write({"tracking": "serial"})
        self.bom.consumption = 'strict'
        self.bom.bom_line_ids.filtered(lambda bl: bl.product_id != self.comp1).unlink()
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        subcontract_location = self.subcontractor_partner1.property_stock_subcontractor

        self.env['stock.quant']._update_available_quantity(self.comp1, subcontract_location, 1)

        receipt = self.env['stock.picking'].create({
            'partner_id': self.subcontractor_partner1.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [
                Command.create({
                    'name': self.finished.name,
                    'product_id': self.finished.id,
                    'product_uom_qty': 2,
                    'product_uom': self.finished.uom_id.id,
                    'location_id': supplier_location.id,
                    'location_dest_id': self.warehouse.lot_stock_id.id,
                })
            ],
        })

        receipt.action_confirm()
        receipt.move_ids.next_serial = "0001"
        receipt.move_ids._generate_serial_numbers(2)
        receipt.button_validate()

        productions = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], order='id')
        fns_produced_qty = sum(productions.filtered(lambda p: p.state == 'done').mapped('qty_producing'))
        self.assertEqual(fns_produced_qty, 2)

        cmp1_consumed_qty = sum(productions.move_raw_ids.filtered(lambda m: m.state == 'done').mapped("quantity_done"))
        self.assertEqual(cmp1_consumed_qty, 2)


@tagged('post_install', '-at_install')
class TestSubcontractingTracking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

        # 1: Create a subcontracting partner
        main_company_1 = cls.env['res.partner'].create({'name': 'main_partner'})
        cls.subcontractor_partner1 = cls.env['res.partner'].create({
            'name': 'Subcontractor 1',
            'parent_id': main_company_1.id,
            'company_id': cls.env.ref('base.main_company').id
        })

        # 2. Create a BOM of subcontracting type
        # 2.1. Comp1 has tracking by lot
        cls.comp1_sn = cls.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'serial'
        })
        cls.comp2 = cls.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        # 2.2. Finished prodcut has tracking by serial number
        cls.finished_product = cls.env['product.product'].create({
            'name': 'finished',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'lot'
        })
        bom_form = Form(cls.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.consumption = 'strict'
        bom_form.subcontractor_ids.add(cls.subcontractor_partner1)
        bom_form.product_tmpl_id = cls.finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp1_sn
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp2
            bom_line.product_qty = 1
        cls.bom_tracked = bom_form.save()

    def test_flow_tracked_1(self):
        """ This test mimics test_flow_1 but with a BoM that has tracking included in it.
        """
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished_product
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # We should be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'mandatory')

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_tracked.id)])
        self.assertEqual(len(mo), 1)
        self.assertEqual(len(mo.picking_ids), 0)
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEqual(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # Create a RR
        pg1 = self.env['procurement.group'].create({})
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'xxx',
            'product_id': self.comp1_sn.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
            'location_id': self.env.user.company_id.subcontracting_location_id.id,
            'group_id': pg1.id,
        })

        # Run the scheduler and check the created picking
        self.env['procurement.group'].run_scheduler()
        picking = self.env['stock.picking'].search([('group_id', '=', pg1.id)])
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.picking_type_id, wh.subcontracting_resupply_type_id)

        lot_id = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.finished_product.id,
            'company_id': self.env.company.id,
        })
        serial_id = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': self.comp1_sn.id,
            'company_id': self.env.company.id,
        })

        action = picking_receipt.action_record_components()
        mo = self.env['mrp.production'].browse(action['res_id'])
        mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
        mo_form.qty_producing = 1
        mo_form.lot_producing_id = lot_id
        with mo_form.move_line_raw_ids.edit(0) as ml:
            ml.lot_id = serial_id
        mo = mo_form.save()
        mo.subcontracting_record_component()

        # We should not be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1_sn, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished_product, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -1)
        self.assertEqual(avail_qty_comp2, -1)
        self.assertEqual(avail_qty_finished, 1)

    def test_flow_tracked_only_finished(self):
        """ Test when only the finished product is tracked """
        self.finished_product.tracking = "serial"
        self.comp1_sn.tracking = "none"
        nb_finished_product = 3
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished_product
            move.product_uom_qty = nb_finished_product
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # We shouldn't be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        wh = picking_receipt.picking_type_id.warehouse_id
        lot_names_finished = [f"subtracked_{i}" for i in range(nb_finished_product)]

        move_details = Form(picking_receipt.move_ids, view='stock.view_stock_move_nosuggest_operations')
        for lot_name in lot_names_finished:
            with move_details.move_line_nosuggest_ids.new() as ml:
                ml.qty_done = 1
                ml.lot_name = lot_name
        move_details.save()

        picking_receipt.button_validate()
        # Check the created manufacturing order
        # Should have one mo by serial number
        mos = picking_receipt.move_ids.move_orig_ids.production_id
        self.assertEqual(len(mos), nb_finished_product)
        self.assertEqual(mos.mapped("state"), ["done"] * nb_finished_product)
        self.assertEqual(mos.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mos.picking_type_id.active)
        self.assertEqual(set(mos.lot_producing_id.mapped("name")), set(lot_names_finished))

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1_sn, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished_product, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -nb_finished_product)
        self.assertEqual(avail_qty_comp2, -nb_finished_product)
        self.assertEqual(avail_qty_finished, nb_finished_product)

    def test_flow_tracked_backorder(self):
        """ This test uses tracked (serial and lot) component and tracked (serial) finished product """
        todo_nb = 4
        self.comp2.tracking = 'lot'
        self.finished_product.tracking = 'serial'

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished_product
            move.product_uom_qty = todo_nb
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # We should be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'mandatory')

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_tracked.id)])
        self.assertEqual(len(mo), 1)
        self.assertEqual(len(mo.picking_ids), 0)
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEqual(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        lot_comp2 = self.env['stock.lot'].create({
            'name': 'lot_comp2',
            'product_id': self.comp2.id,
            'company_id': self.env.company.id,
        })
        serials_finished = []
        serials_comp1 = []
        for i in range(todo_nb):
            serials_finished.append(self.env['stock.lot'].create({
                'name': 'serial_fin_%s' % i,
                'product_id': self.finished_product.id,
                'company_id': self.env.company.id,
            }))
            serials_comp1.append(self.env['stock.lot'].create({
                'name': 'serials_comp1_%s' % i,
                'product_id': self.comp1_sn.id,
                'company_id': self.env.company.id,
            }))

        for i in range(todo_nb):
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.lot_producing_id = serials_finished[i]
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1_sn)
                ml.lot_id = serials_comp1[i]
            with mo_form.move_line_raw_ids.edit(1) as ml:
                self.assertEqual(ml.product_id, self.comp2)
                ml.lot_id = lot_comp2
            mo = mo_form.save()
            mo.subcontracting_record_component()

        # We should not be able to call the 'record_components' button
        self.assertEqual(picking_receipt.display_action_record_components, 'hide')

        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.mapped("state"), ['done'] * todo_nb)
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), todo_nb)
        self.assertEqual(mo.procurement_group_id.mrp_production_ids.mapped("qty_produced"), [1] * todo_nb)

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1_sn, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished_product, wh.lot_stock_id)
        self.assertEqual(avail_qty_comp1, -todo_nb)
        self.assertEqual(avail_qty_comp2, -todo_nb)
        self.assertEqual(avail_qty_finished, todo_nb)

    def test_flow_tracked_backorder02(self):
        """ Both component and finished product are tracked by lot. """
        todo_nb = 4
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        finished_product, component = self.env['product.product'].create([{
            'name': 'SuperProduct',
            'type': 'product',
            'tracking': 'lot',
        }, {
            'name': 'Component',
            'type': 'product',
            'tracking': 'lot',
            'route_ids': [(4, resupply_sub_on_order_route.id)],
        }])

        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.subcontractor_ids.add(self.subcontractor_partner1)
        bom_form.product_tmpl_id = finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = component
            bom_line.product_qty = 1
        bom = bom_form.save()

        finished_lot, component_lot = self.env['stock.lot'].create([{
            'name': 'lot_%s' % product.name,
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for product in [finished_product, component]])

        self.env['stock.quant']._update_available_quantity(component, self.env.ref('stock.stock_location_stock'), todo_nb, lot_id=component_lot)

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = finished_product
            move.product_uom_qty = todo_nb
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', bom.id)])

        # Process the delivery of the components
        compo_picking = mo.picking_ids
        compo_picking.action_assign()
        wizard_data = compo_picking.button_validate()
        wizard = Form(self.env[wizard_data['res_model']].with_context(wizard_data['context'])).save()
        wizard.process()

        for qty in [3, 1]:
            # Record the receiption of <qty> finished products
            picking_receipt = self.env['stock.picking'].search([('partner_id', '=', self.subcontractor_partner1.id), ('state', '!=', 'done')])
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.qty_producing = qty
            mo_form.lot_producing_id = finished_lot
            with mo_form.move_line_raw_ids.edit(0) as ml:
                ml.lot_id = component_lot
            mo = mo_form.save()
            mo.subcontracting_record_component()

            # Validate the picking and create a backorder
            wizard_data = picking_receipt.button_validate()
            if qty == 3:
                wizard = Form(self.env[wizard_data['res_model']].with_context(wizard_data['context'])).save()
                wizard.process()

            self.assertEqual(picking_receipt.state, 'done')

    def test_flow_backorder_production(self):
        """ Test subcontracted MO backorder (i.e. through record production window, NOT through
        picking backorder). Finished product is serial tracked to ensure subcontracting MO window
        is opened. Check that MO backorder auto-reserves components
        """
        todo_nb = 3
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        finished_product, component = self.env['product.product'].create([{
            'name': 'Pepper Spray',
            'type': 'product',
            'tracking': 'serial',
        }, {
            'name': 'Pepper',
            'type': 'product',
            'route_ids': [(4, resupply_sub_on_order_route.id)],
        }])

        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.subcontractor_ids.add(self.subcontractor_partner1)
        bom_form.product_tmpl_id = finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = component
            bom_line.product_qty = 1
        bom = bom_form.save()

        finished_serials = self.env['stock.lot'].create([{
            'name': 'sn_%s' % str(i),
            'product_id': finished_product.id,
            'company_id': self.env.company.id,
        } for i in range(todo_nb)])

        self.env['stock.quant']._update_available_quantity(component, self.env.ref('stock.stock_location_stock'), todo_nb)

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = finished_product
            move.product_uom_qty = todo_nb
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', bom.id)])

        # Process the delivery of the components
        compo_picking = mo.picking_ids
        compo_picking.action_assign()
        wizard_data = compo_picking.button_validate()
        wizard = Form(self.env[wizard_data['res_model']].with_context(wizard_data['context'])).save()
        wizard.process()

        picking_receipt = self.env['stock.picking'].search([('partner_id', '=', self.subcontractor_partner1.id), ('state', '!=', 'done')])
        for sn in finished_serials:
            # Record the production of each serial number separately
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            self.assertEqual(mo.move_raw_ids.state, 'assigned')
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.qty_producing = 1
            mo_form.lot_producing_id = sn
            mo = mo_form.save()
            mo.subcontracting_record_component()

        # Validate the picking
        picking_receipt.button_validate()
        self.assertEqual(picking_receipt.state, 'done')


@tagged('post_install', '-at_install')
class TestSubcontractingPortal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})
        # 1: Create a subcontracting partner
        main_partner = cls.env['res.partner'].create({'name': 'main_partner'})
        cls.subcontractor_partner1 = cls.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'parent_id': main_partner.id,
            'company_id': cls.env.ref('base.main_company').id,
        })
        # Make the subcontracting partner a portal user
        cls.portal_user = cls.env['res.users'].create({
            'name': 'portal user (subcontractor)',
            'partner_id': cls.subcontractor_partner1.id,
            'login': 'subcontractor',
            'password': 'subcontractor',
            'email': 'subcontractor@subcontracting.portal',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id, cls.env.ref('stock.group_production_lot').id])]
        })

        # 2. Create a BOM of subcontracting type
        # 2.1. Comp1 has tracking by lot
        cls.comp1_sn = cls.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'serial'
        })
        cls.comp2 = cls.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_not_in_bom = cls.env['product.product'].create({
            'name': 'Product not in the BoM',
            'type': 'product',
        })

        # 2.2. Finished prodcut has tracking by serial number
        cls.finished_product = cls.env['product.product'].create({
            'name': 'finished',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'lot'
        })
        bom_form = Form(cls.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.consumption = 'warning'
        bom_form.subcontractor_ids.add(cls.subcontractor_partner1)
        bom_form.product_tmpl_id = cls.finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp1_sn
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp2
            bom_line.product_qty = 1
        cls.bom_tracked = bom_form.save()

    def test_flow_subcontracting_portal(self):
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished_product
            move.product_uom_qty = 2
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # Using the subcontractor (portal user)
        lot1 = self.env['stock.lot'].with_user(self.portal_user).create({
            'name': 'lot1',
            'product_id': self.finished_product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].with_user(self.portal_user).create({
            'name': 'lot2',
            'product_id': self.finished_product.id,
            'company_id': self.env.company.id,
        })
        serial1 = self.env['stock.lot'].with_user(self.portal_user).create({
            'name': 'lot1',
            'product_id': self.comp1_sn.id,
            'company_id': self.env.company.id,
        })
        serial2 = self.env['stock.lot'].with_user(self.portal_user).create({
            'name': 'lot2',
            'product_id': self.comp1_sn.id,
            'company_id': self.env.company.id,
        })
        serial3 = self.env['stock.lot'].with_user(self.portal_user).create({
            'name': 'lot3',
            'product_id': self.comp1_sn.id,
            'company_id': self.env.company.id,
        })
        action = picking_receipt.with_user(self.portal_user).with_context({'is_subcontracting_portal': 1}).move_ids.action_show_details()
        mo = self.env['mrp.production'].with_user(self.portal_user).browse(action['res_id'])
        mo_form = Form(mo.with_context(action['context']), view=action['view_id'])
        # Registering components for the first manufactured product
        mo_form.qty_producing = 1
        mo_form.lot_producing_id = lot1
        with mo_form.move_line_raw_ids.edit(0) as ml:
            ml.lot_id = serial1
        mo = mo_form.save()
        mo.subcontracting_record_component()
        # Continue record of components with new MO (backorder was when recording first MO)
        action = picking_receipt.with_user(self.portal_user).with_context({'is_subcontracting_portal': 1}).move_ids.action_show_details()
        mo = self.env['mrp.production'].with_user(self.portal_user).browse(action['res_id'])
        mo_form = Form(mo.with_context(action['context']), view=action['view_id'])
        # Registering components for the second manufactured product with over-consumption, which leads to a warning
        mo_form.qty_producing = 1
        mo_form.lot_producing_id = lot2
        with mo_form.move_line_raw_ids.edit(0) as ml:
            ml.lot_id = serial2
        with mo_form.move_line_raw_ids.new() as ml:
            ml.product_id = self.comp1_sn
            ml.lot_id = serial3
        with mo_form.move_line_raw_ids.edit(1) as ml:
            ml.qty_done = 2
        # The portal user should not be able to add a product not in the BoM
        with self.assertRaises(AccessError):
            with mo_form.move_line_raw_ids.new() as ml:
                ml.product_id = self.product_not_in_bom
        mo = mo_form.save()
        action_warning = mo.subcontracting_record_component()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action_warning['context']))
        warning = warning.save()
        warning.action_confirm()

        # Attempt to validate from the portal user should give an error
        with self.assertRaises(UserError):
            picking_receipt.with_user(self.portal_user).button_validate()

        # Validation from the backend user
        picking_receipt.button_validate()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_line_raw_ids[0].qty_done, 1)
        self.assertEqual(mo.move_line_raw_ids[0].lot_id, serial2)
        self.assertEqual(mo.move_line_raw_ids[1].qty_done, 1)
        self.assertEqual(mo.move_line_raw_ids[1].lot_id, serial3)
        self.assertEqual(mo.move_line_raw_ids[2].qty_done, 2)
class TestSubcontractingSerialMassReceipt(TransactionCase):

    def setUp(self):
        super().setUp()
        self.subcontractor = self.env['res.partner'].create({
            'name': 'Subcontractor',
        })
        self.resupply_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        self.raw_material = self.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
            'route_ids': [Command.link(self.resupply_route.id)],
        })
        self.finished = self.env['product.product'].create({
            'name': 'Finished',
            'type': 'product',
            'tracking': 'serial'
        })
        self.bom = self.env['mrp.bom'].create({
            'product_id': self.finished.id,
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(self.subcontractor.id)],
            'consumption': 'strict',
            'bom_line_ids': [
                Command.create({'product_id': self.raw_material.id, 'product_qty': 1}),
            ]
        })

    def test_receive_after_resupply(self):
        quantities = [5, 4, 1]
        # Make needed component stock
        self.env['stock.quant']._update_available_quantity(self.raw_material, self.env.ref('stock.stock_location_stock'), sum(quantities))
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = sum(quantities)
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        # Process the delivery of the components
        picking_deliver = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)]).picking_ids
        picking_deliver.action_assign()
        picking_deliver.button_validate()
        wizard_data = picking_deliver.button_validate()
        wizard = Form(self.env[wizard_data['res_model']].with_context(wizard_data['context'])).save()
        wizard.process()
        # Receive
        for quantity in quantities:
            # Receive <quantity> finished products
            Form(self.env['stock.assign.serial'].with_context(
                default_move_id=picking_receipt.move_ids[0].id,
                default_next_serial_number=self.env['stock.lot']._get_next_serial(picking_receipt.company_id, picking_receipt.move_ids[0].product_id) or 'sn#1',
                default_next_serial_count=quantity,
            )).save().generate_serial_numbers()
            wizard_data = picking_receipt.button_validate()
            if wizard_data is not True:
                # Create backorder
                wizard = Form(self.env[wizard_data['res_model']].with_context(wizard_data['context'])).save()
                wizard.process()
                self.assertEqual(picking_receipt.state, 'done')
                picking_receipt = picking_receipt.backorder_ids[-1]
                self.assertEqual(picking_receipt.state, 'assigned')
        self.assertEqual(picking_receipt.state, 'done')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.raw_material, self.env.ref('stock.stock_location_stock')), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.raw_material, self.subcontractor.property_stock_subcontractor), 0)

    def test_receive_no_resupply(self):
        quantity = 5
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = quantity
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        # Receive finished products
        Form(self.env['stock.assign.serial'].with_context(
            default_move_id=picking_receipt.move_ids[0].id,
            default_next_serial_number=self.env['stock.lot']._get_next_serial(picking_receipt.company_id, picking_receipt.move_ids[0].product_id) or 'sn#1',
            default_next_serial_count=quantity,
        )).save().generate_serial_numbers()
        picking_receipt.button_validate()
        self.assertEqual(picking_receipt.state, 'done')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.raw_material, self.env.ref('stock.stock_location_stock')), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.raw_material, self.subcontractor.property_stock_subcontractor, allow_negative=True), -quantity)

    def test_bom_subcontracting_product_dynamic_attribute(self):
        """
            Test that the report BOM data is available for a product with an dynamic attribute
            but without variant.
        """
        dynamic_attribute = self.env['product.attribute'].create({
            'name': 'flavour',
            'create_variant': 'dynamic',
        })
        value_1 = self.env['product.attribute.value'].create({
            'name': 'Vanilla',
            'attribute_id': dynamic_attribute.id,
        })
        value_2 = self.env['product.attribute.value'].create({
            'name': 'Chocolate',
            'attribute_id': dynamic_attribute.id,
        })
        product_template = self.env['product.template'].create({
            'name': 'Cake',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'detailed_type': 'product',
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': dynamic_attribute.id,
            'value_ids': [Command.set([value_1.id, value_2.id])],
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'type': 'subcontract',
            'subcontractor_ids': [Command.set([self.subcontractor.id])],
        })
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id, searchVariant=False)
        self.assertTrue(report_values)

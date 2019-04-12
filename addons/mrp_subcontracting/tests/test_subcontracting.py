# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase

from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestSubcontractingBasic(TransactionCase):
    def test_partner_1(self):
        """ Checks the `display_name` of subcontracted partners. """
        main_partner = self.env['res.partner'].create({'name': 'main_partner'})

        # When a name is set to the subcontracted partner.
        subcontractor_partner1 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'type': 'subcontractor',
            'parent_id': main_partner.id,
        })
        self.assertEqual(subcontractor_partner1.display_name, "main_partner, subcontractor_partner, Subcontractor")

        # When a name is not set to the subcontracted partner.
        subcontractor_partner1 = self.env['res.partner'].create({
            'name': '',
            'type': 'subcontractor',
            'parent_id': main_partner.id,
        })
        self.assertEqual(subcontractor_partner1.display_name, "main_partner, Subcontractor")

    def test_partner_2(self):
        """ Open an existing partner and add a contact of type subcontractor (simple form view).
        Checks the customer and supplier locations are set to the subcontracting one onces saved.
        """
        that_company = self.env['res.partner'].create({
            'is_company': True,
            'name': "That Company",
        })
        partner_form = Form(that_company)
        with partner_form.child_ids.new() as partner:
            partner.name = 'That Guy'
            partner.type = 'subcontractor'
        partner_form.save()
        subcontractor = that_company.child_ids
        self.assertEquals(subcontractor.property_stock_supplier, self.env.user.company_id.subcontracting_location_id)
        self.assertEquals(subcontractor.property_stock_customer, self.env.user.company_id.subcontracting_location_id)

    def test_partner_3(self):
        """ Create a new partner, select a parent company, and choose type subcontractor (debug
        active). Checks the onchange correctly set the customer and supplier locations to the
        subcontracting ones. Change them to another one, save, checks they are rightly applied.
        """
        # FIXME sle: this field should not be writeable without the debug mode but it is. ask xmo
        group_no_one = self.env.ref('base.group_no_one')
        self.env.user.write({'groups_id': [(3, group_no_one.id)]})
        partner_form = Form(self.env['res.partner'])
        partner_form.name = 'subcontractor partner'
        self.assertNotEqual(partner_form.property_stock_supplier, self.env.user.company_id.subcontracting_location_id)
        self.assertNotEqual(partner_form.property_stock_customer, self.env.user.company_id.subcontracting_location_id)
        partner_form.type = 'subcontractor'
        self.assertEqual(partner_form.property_stock_supplier, self.env.user.company_id.subcontracting_location_id)
        self.assertEqual(partner_form.property_stock_customer, self.env.user.company_id.subcontracting_location_id)
        subcontracting_location2 = self.env.user.company_id.subcontracting_location_id.copy()
        partner_form.property_stock_supplier = subcontracting_location2
        partner_form.property_stock_customer = subcontracting_location2
        partner = partner_form.save()
        self.assertEqual(partner.property_stock_supplier, subcontracting_location2)
        self.assertEqual(partner.property_stock_customer, subcontracting_location2)

    def test_partner_4(self):
        """ Create a new partner, select a parent company, and choose type subcontractor (debug
        not active). Checks the customer and supplier locations are set to the subcontracting one
        onces saved.
        """
        that_company = self.env['res.partner'].create({
            'is_company': True,
            'name': "That Company",
        })
        partner_form = Form(self.env['res.partner'])
        partner_form.name = 'That Guy'
        partner_form.parent_id = that_company
        partner_form.type = 'subcontractor'
        subcontractor = partner_form.save()
        self.assertEquals(subcontractor.property_stock_supplier, self.env.user.company_id.subcontracting_location_id)
        self.assertEquals(subcontractor.property_stock_customer, self.env.user.company_id.subcontracting_location_id)

    def test_partner_5(self):
        """ Create a new partner with a child partner of type contact,
        then write the type 'subcontractor' on it
        """
        that_company = self.env['res.partner'].create({
            'is_company': True,
            'name': "That Company",
        })
        partner_form = Form(that_company)
        with partner_form.child_ids.new() as partner:
            partner.name = 'That Guy'
            partner.type = 'contact'
        partner_form.save()

        # We write a new type on the created child partner
        subcontractor = that_company.child_ids
        self.assertEquals(len(that_company.child_ids), 1)
        subcontractor.type = 'subcontractor'

        self.assertEquals(subcontractor.property_stock_supplier, self.env.user.company_id.subcontracting_location_id)
        self.assertEquals(subcontractor.property_stock_customer, self.env.user.company_id.subcontracting_location_id)

    def test_subcontracting_location_1(self):
        """ Checks the creation and presence of the subcontracting location. """
        self.assertTrue(self.env.user.company_id.subcontracting_location_id)
        self.assertTrue(self.env.user.company_id.subcontracting_location_id.active)
        company2 = self.env['res.company'].create({'name': 'Test Company'})
        self.assertTrue(company2.subcontracting_location_id)


class TestSubcontractingFlows(TransactionCase):
    def setUp(self):
        super(TestSubcontractingFlows, self).setUp()
        # 1: Create a subcontracting partner
        main_partner = self.env['res.partner'].create({'name': 'main_partner'})
        self.subcontractor_partner1 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'type': 'subcontractor',
            'parent_id': main_partner.id,
        })

        # 2. Create a BOM of subcontracting type
        self.comp1 = self.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.comp2 = self.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.finished = self.env['product.product'].create({
            'name': 'finished',
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
            bom_line.product_id = self.comp2
            bom_line.product_qty = 1
        self.bom = bom_form.save()

        # Create a BoM for self.comp2
        self.comp2comp = self.env['product.product'].create({
            'name': 'component for Component2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        bom_form = Form(self.env['mrp.bom'])
        bom_form.product_tmpl_id = self.comp2.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp2comp
            bom_line.product_qty = 1
        self.comp2_bom = bom_form.save()

    def test_flow_1(self):
        """ Don't tick any route on the components and trigger the creation of the subcontracting
        manufacturing order through a receipt picking. Create a reordering rule in the
        subcontracting locations for a component and run the scheduler to resupply. Checks if the
        resupplying actually works
        """
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
        self.assertFalse(picking_receipt.display_action_record_components)
        self.assertFalse(picking_receipt.display_view_subcontracted_move_lines)

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo), 1)
        self.assertEqual(len(mo.picking_ids), 0)
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEquals(mo.picking_type_id, wh.subcontracting_type_id)
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
        self.assertEquals(picking.picking_type_id, wh.out_type_id)
        picking_receipt.move_lines.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEquals(mo.state, 'done')

        # Now that the picking is done, the details stat button should be visible
        self.assertTrue(picking_receipt.display_view_subcontracted_move_lines)

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEquals(avail_qty_comp1, -1)
        self.assertEquals(avail_qty_comp2, -1)
        self.assertEquals(avail_qty_finished, 1)

    def test_flow_2(self):
        """ Tick "Resupply Subcontractor on Order" on the components and trigger the creation of
        the subcontracting manufacturing order through a receipt picking. Checks if the resupplying
        actually works.
        """
        # Tick "resupply subconractor on order"
        resupply_sub_on_order_route = self.env['stock.location.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(4, resupply_sub_on_order_route.id, None)]})

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
        self.assertFalse(picking_receipt.display_action_record_components)
        self.assertFalse(picking_receipt.display_view_subcontracted_move_lines)

        # Pickings should directly be created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo.picking_ids), 1)
        self.assertEquals(mo.state, 'to_close')
        self.assertEqual(len(mo.picking_ids.move_lines), 2)

        picking = mo.picking_ids
        wh = picking.picking_type_id.warehouse_id

        # The picking should be a delivery order
        self.assertEquals(picking.picking_type_id, wh.out_type_id)

        self.assertEquals(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # No manufacturing order for `self.comp2`
        comp2mo = self.env['mrp.production'].search([('bom_id', '=', self.comp2_bom.id)])
        self.assertEqual(len(comp2mo), 0)

        picking_receipt.move_lines.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEquals(mo.state, 'done')

        # Now that the picking is done, the details stat button should be visible
        self.assertTrue(picking_receipt.display_view_subcontracted_move_lines)

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEquals(avail_qty_comp1, -1)
        self.assertEquals(avail_qty_comp2, -1)
        self.assertEquals(avail_qty_finished, 1)

    def test_flow_3(self):
        """ Tick "Resupply Subcontractor on Order" and "MTO" on the components and trigger the
        creation of the subcontracting manufacturing order through a receipt picking. Checks if the
        resupplying actually works. One of the component has also "manufacture" set and a BOM
        linked. Checks that an MO is created for this one.
        """
        # Tick "resupply subconractor on order"
        resupply_sub_on_order_route = self.env['stock.location.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(4, resupply_sub_on_order_route.id, None)]})

        # Tick "manufacture" and MTO on self.comp2
        mto_route = self.env['stock.location.route'].search([('name', '=', 'Replenish on Order (MTO)')])
        manufacture_route = self.env['stock.location.route'].search([('name', '=', 'Manufacture')])
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
        self.assertFalse(picking_receipt.display_action_record_components)
        self.assertFalse(picking_receipt.display_view_subcontracted_move_lines)

        # Pickings should directly be created
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(len(mo.picking_ids), 1)
        self.assertEquals(mo.state, 'to_close')
        self.assertEqual(len(mo.picking_ids.move_lines), 2)

        # The picking should be a delivery order
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEquals(mo.picking_ids.picking_type_id, wh.out_type_id)

        self.assertEquals(mo.picking_type_id, wh.subcontracting_type_id)
        self.assertFalse(mo.picking_type_id.active)

        # As well as a manufacturing order for `self.comp2`
        comp2mo = self.env['mrp.production'].search([('bom_id', '=', self.comp2_bom.id)])
        self.assertEqual(len(comp2mo), 1)
        picking_receipt.move_lines.quantity_done = 1
        picking_receipt.button_validate()
        self.assertEquals(mo.state, 'done')

        # Now that the picking is done, the details stat button should be visible
        self.assertTrue(picking_receipt.display_view_subcontracted_move_lines)

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished, wh.lot_stock_id)
        self.assertEquals(avail_qty_comp1, -1)
        self.assertEquals(avail_qty_comp2, -1)
        self.assertEquals(avail_qty_finished, 1)

    def test_flow_4(self):
        """ Check that the correct BoM is chosen accordingly to the partner
        """
        # We create a second partner of type subcontractor
        main_partner_2 = self.env['res.partner'].create({'name': 'main_partner'})
        subcontractor_partner2 = self.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'type': 'subcontractor',
            'parent_id': main_partner_2.id,
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

        mo_pick1 = picking_receipt1.move_lines.mapped('move_orig_ids.production_id')
        mo_pick2 = picking_receipt2.move_lines.mapped('move_orig_ids.production_id')
        self.assertEquals(len(mo_pick1), 1)
        self.assertEquals(len(mo_pick2), 1)
        self.assertEquals(mo_pick1.bom_id, self.bom)
        self.assertEquals(mo_pick2.bom_id, bom2)


class TestSubcontractingTracking(TransactionCase):
    def setUp(self):
        super(TestSubcontractingTracking, self).setUp()
        # 1: Create a subcontracting partner
        main_company_1 = self.env['res.partner'].create({'name': 'main_partner'})
        self.subcontractor_partner1 = self.env['res.partner'].create({
            'name': 'Subcontractor 1',
            'type': 'subcontractor',
            'parent_id': main_company_1.id,
        })

        # 2. Create a BOM of subcontracting type
        # 2.1. Comp1 has tracking by lot
        self.comp1_sn = self.env['product.product'].create({
            'name': 'Component1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'serial'
        })
        self.comp2 = self.env['product.product'].create({
            'name': 'Component2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        # 2.2. Finished prodcut has tracking by serial number
        self.finished_lot = self.env['product.product'].create({
            'name': 'finished',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot'
        })
        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.product_tmpl_id = self.finished_lot.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp1_sn
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp2
            bom_line.product_qty = 1
        self.bom_tracked = bom_form.save()

    def test_flow_tracked_1(self):
        """ This test mimics test_flow_1 but with a BoM that has tracking included in it.
        """
        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished_lot
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()

        # We should be able to call the 'record_components' button
        self.assertTrue(picking_receipt.display_action_record_components)
        self.assertFalse(picking_receipt.display_view_subcontracted_move_lines)

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_tracked.id)])
        self.assertEqual(len(mo), 1)
        self.assertEquals(mo.state, 'confirmed')
        self.assertEqual(len(mo.picking_ids), 0)
        wh = picking_receipt.picking_type_id.warehouse_id
        self.assertEquals(mo.picking_type_id, wh.subcontracting_type_id)
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
        self.assertEquals(picking.picking_type_id, wh.out_type_id)

        lot_id = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.finished_lot.id
        })
        serial_id = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.comp1_sn.id
        })
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.final_lot_id = lot_id
        produce_form.workorder_line_ids._records[0]['lot_id'] = serial_id.id
        wiz_produce = produce_form.save()
        wiz_produce.do_produce()

        # We should not be able to call the 'record_components' button
        self.assertFalse(picking_receipt.display_action_record_components)
        # We should see the move lines stat button
        self.assertTrue(picking_receipt.display_view_subcontracted_move_lines)

        picking_receipt.move_lines.quantity_done = 1
        picking_receipt.move_lines.move_line_ids.lot_name = 'lot00001test'
        picking_receipt.button_validate()
        self.assertEquals(mo.state, 'done')

        # Available quantities should be negative at the subcontracting location for each components
        avail_qty_comp1 = self.env['stock.quant']._get_available_quantity(self.comp1_sn, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_comp2 = self.env['stock.quant']._get_available_quantity(self.comp2, self.subcontractor_partner1.property_stock_supplier, allow_negative=True)
        avail_qty_finished = self.env['stock.quant']._get_available_quantity(self.finished_lot, wh.lot_stock_id)
        self.assertEquals(avail_qty_comp1, -1)
        self.assertEquals(avail_qty_comp2, -1)
        self.assertEquals(avail_qty_finished, 1)

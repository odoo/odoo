# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.addons.mrp_subcontracting.tests.test_subcontracting import TestSubcontractingPortal


class TestSubcontractingDropshippingFlows(TestMrpSubcontractingCommon):

    def test_mrp_subcontracting_dropshipping_1(self):
        """ Mark the subcontracted product with the route dropship and add the
        subcontractor as seller. The component has the routes 'MTO', 'Replenish
        on order' and 'Buy'. Also another partner is set as vendor on the comp.
        Create a SO and check that:
        - Delivery between subcontractor and customer for subcontracted product.
        - Delivery for the component to the subcontractor for the specified wh.
        - Po created for the component.
        """
        self.warehouse.manufacture_pull_id.route_id.write({'sequence': 20})
        self.env.ref('stock.route_warehouse0_mto').active = True
        mto_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')])
        resupply_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        resupply_route.product_selectable = True
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')])
        dropship_route = self.env['stock.route'].search([('name', '=', 'Dropship')])
        self.comp2.write({'route_ids': [(4, buy_route.id), (4, mto_route.id), (4, resupply_route.id)]})
        self.finished.write({'route_ids': [(4, dropship_route.id)]})

        warehouse = self.env['stock.warehouse'].create({
            'name': 'Warehouse For subcontract',
            'code': 'WFS'
        })

        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id
        })

        partner = self.env['res.partner'].create({
            'name': 'Toto'
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': partner.id
        })

        # Create a receipt picking from the subcontractor
        so_form = Form(self.env['sale.order'].sudo())
        so_form.partner_id = partner
        so_form.warehouse_id = warehouse
        with so_form.order_line.new() as line:
            line.product_id = self.finished
            line.product_uom_qty = 1
        so = so_form.save()
        so.action_confirm()

        # Pickings should directly be created
        po = self.env['purchase.order'].search([('origin', 'ilike', so.name)])
        self.assertTrue(po)

        po.button_approve()

        picking_finished = po.picking_ids
        self.assertEqual(len(picking_finished), 1.0)
        self.assertEqual(picking_finished.location_dest_id, partner.property_stock_customer)
        self.assertEqual(picking_finished.location_id, self.subcontractor_partner1.property_stock_supplier)
        self.assertEqual(picking_finished.state, 'assigned')

        picking_delivery = self.env['stock.move'].search([
            ('product_id', '=', self.comp2.id),
            ('location_id', '=', warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.subcontractor_partner1.property_stock_subcontractor.id),
        ]).picking_id
        self.assertTrue(picking_delivery)
        self.assertEqual(picking_delivery.state, 'waiting')

        po = self.env['purchase.order.line'].search([
            ('product_id', '=', self.comp2.id),
            ('partner_id', '=', partner.id),
        ]).order_id
        self.assertTrue(po)

    def test_mrp_subcontracting_purchase_2(self):
        """Let's consider a subcontracted BOM with 1 component. Tick "Resupply Subcontractor on Order" on the component and set a supplier on it.
        Purchase 1 BOM to the subcontractor. Confirm the purchase and change the purchased quantity to 2.
        Check that 2 components are delivered to the subcontractor
        """
        # Tick "resupply subconractor on order on component"
        self.bom.bom_line_ids = [(5, 0, 0)]
        self.bom.bom_line_ids = [(0, 0, {'product_id': self.comp1.id, 'product_qty': 1})]
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        resupply_sub_on_order_route.product_selectable = True
        (self.comp1).write({'route_ids': [(4, resupply_sub_on_order_route.id, None)]})
        # Create a supplier and set it to component
        vendor = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        self.env['product.supplierinfo'].create({
            'product_id': self.finished.id,
            'partner_id': vendor.id,
            'price': 50,
        })
        self.comp1.write({'seller_ids': [(0, 0, {'partner_id': vendor.id, 'product_code': 'COMP1'})]})
        # Purchase 1 BOM to the subcontractor
        po = Form(self.env['purchase.order'])
        po.partner_id = self.subcontractor_partner1
        with po.order_line.new() as po_line:
            po_line.product_id = self.finished
            po_line.product_qty = 1
            po_line.price_unit = 100
        po = po.save()
        # Confirm the purchase
        po.button_confirm()
        # Check one delivery order with the component has been created for the subcontractor
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(mo.state, 'confirmed')
        # Check that 1 delivery with 1 component for the subcontractor has been created
        picking_delivery = mo.picking_ids
        wh = picking_delivery.picking_type_id.warehouse_id
        origin = picking_delivery.origin
        self.assertEqual(len(picking_delivery), 1)
        self.assertEqual(len(picking_delivery.move_ids_without_package), 1)
        self.assertEqual(picking_delivery.picking_type_id, wh.subcontracting_resupply_type_id)
        self.assertEqual(picking_delivery.partner_id, self.subcontractor_partner1)

        # Change the purchased quantity to 2
        po.order_line.write({'product_qty': 2})
        # Check that a single delivery with the two components for the subcontractor have been created
        picking_deliveries = self.env['stock.picking'].search([('origin', '=', origin)])
        self.assertEqual(len(picking_deliveries), 1)
        self.assertEqual(picking_deliveries.picking_type_id, wh.subcontracting_resupply_type_id)
        self.assertEqual(picking_deliveries.partner_id, self.subcontractor_partner1)
        self.assertTrue(picking_deliveries.state != 'cancel')
        move1 = picking_deliveries.move_ids_without_package
        self.assertEqual(move1.product_id, self.comp1)
        self.assertEqual(move1.product_uom_qty, 2)

    def test_dropshipped_component_and_sub_location(self):
        """
        Suppose:
            - a subcontracted product and a component dropshipped to the subcontractor
            - the location of the subcontractor is a sub-location of the main subcontrating location
        This test ensures that the PO that brings the component to the subcontractor has a correct
        destination address
        """
        subcontract_location = self.env.company.subcontracting_location_id
        sub_location = self.env['stock.location'].create({
            'name': 'Super Location',
            'location_id': subcontract_location.id,
            'is_subcontracting_location': True,
        })

        dropship_route = self.env['stock.route'].search([('name', '=', 'Dropship')])

        subcontractor, vendor = self.env['res.partner'].create([
            {'name': 'SuperSubcontractor', 'property_stock_subcontractor': sub_location.id},
            {'name': 'SuperVendor'},
        ])

        p_finished, p_compo = self.env['product.product'].create([{
            'name': 'Finished Product',
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': subcontractor.id})],
        }, {
            'name': 'Component',
            'type': 'consu',
            'seller_ids': [(0, 0, {'partner_id': vendor.id})],
            'route_ids': [(6, 0, dropship_route.ids)]
        }])

        self.env['mrp.bom'].create({
            'product_tmpl_id': p_finished.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, subcontractor.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': p_compo.id, 'product_qty': 1}),
            ],
        })

        subcontract_po = self.env['purchase.order'].create({
            "partner_id": subcontractor.id,
            "order_line": [(0, 0, {
                'product_id': p_finished.id,
                'name': p_finished.name,
                'product_qty': 1.0,
            })],
        })
        subcontract_po.button_confirm()

        dropship_po = self.env['purchase.order'].search([('partner_id', '=', vendor.id)])
        self.assertEqual(dropship_po.dest_address_id, subcontractor)

    def test_po_to_customer(self):
        """
        Create and confirm a PO with a subcontracted move. The picking type of
        the PO is 'Dropship' and the delivery address a customer. Then, process
        a return with the stock location as destination and another return with
        the supplier as destination
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'group_ids': [(4, grp_multi_loc.id)]})

        subcontractor, client = self.env['res.partner'].create([
            {'name': 'SuperSubcontractor'},
            {'name': 'SuperClient'},
        ])

        p_finished, p_compo = self.env['product.product'].create([{
            'name': 'Finished Product',
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': subcontractor.id})],
        }, {
            'name': 'Component',
            'type': 'consu',
        }])

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': p_finished.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, subcontractor.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': p_compo.id, 'product_qty': 1}),
            ],
        })

        dropship_picking_type = self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('default_location_src_id.usage', '=', 'supplier'),
            ('default_location_dest_id.usage', '=', 'customer'),
        ], limit=1, order='sequence')

        po = self.env['purchase.order'].create({
            "partner_id": subcontractor.id,
            "picking_type_id": dropship_picking_type.id,
            "dest_address_id": client.id,
            "order_line": [(0, 0, {
                'product_id': p_finished.id,
                'name': p_finished.name,
                'product_qty': 2.0,
            })],
        })
        po.button_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', bom.id)])
        self.assertEqual(mo.picking_type_id, self.warehouse.subcontracting_type_id)

        delivery = po.picking_ids
        delivery.move_line_ids.quantity = 2.0
        delivery.move_ids.picked = True
        delivery.button_validate()

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(mo.state, 'done')
        self.assertEqual(po.order_line.qty_received, 2)

        # return 1 x P_finished to the stock location
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=delivery.ids, active_id=delivery.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1.0
        return_wizard = return_form.save()
        delivery_return01 = return_wizard._create_return()
        delivery_return01.move_line_ids.quantity = 1.0
        delivery_return01.move_ids.picked = True
        delivery_return01.location_dest_id = self.warehouse.lot_stock_id
        delivery_return01.button_validate()

        self.assertEqual(delivery_return01.state, 'done')
        self.assertEqual(p_finished.qty_available, 1, 'One product has been returned to the stock location, so it should be available')
        self.assertEqual(po.order_line.qty_received, 2, 'One product has been returned to the stock location, so we should still consider it as received')

        # return 1 x P_finished to the supplier location
        return_form = Form(self.env['stock.return.picking'].with_context(active_ids=delivery.ids, active_id=delivery.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 1.0
        return_wizard = return_form.save()
        delivery_return02 = return_wizard._create_return()
        delivery_return02.location_dest_id = dropship_picking_type.default_location_src_id
        delivery_return02.move_line_ids.quantity = 1.0
        delivery_return02.move_ids.picked = True
        delivery_return02.button_validate()

        self.assertEqual(delivery_return02.state, 'done')
        self.assertEqual(po.order_line.qty_received, 1)

    def test_po_to_subcontractor(self):
        """
        Create and confirm a PO with a subcontracted move. The bought product is
        also a component of another subcontracted product. The picking type of
        the PO is 'Dropship' and the delivery address is the other subcontractor
        """
        subcontractor, super_subcontractor = self.env['res.partner'].create([
            {'name': 'Subcontractor'},
            {'name': 'SuperSubcontractor'},
        ])

        super_product, product, component = self.env['product.product'].create([{
            'name': 'Super Product',
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': super_subcontractor.id})],
        }, {
            'name': 'Product',
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': subcontractor.id})],
        }, {
            'name': 'Component',
            'type': 'consu',
        }])

        _, bom_product = self.env['mrp.bom'].create([{
            'product_tmpl_id': super_product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, super_subcontractor.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': product.id, 'product_qty': 1}),
            ],
        }, {
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, subcontractor.ids)],
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ],
        }])

        po = self.env['purchase.order'].create({
            "partner_id": subcontractor.id,
            "picking_type_id": self.env.company.dropship_subcontractor_pick_type_id.id,
            "dest_address_id": super_subcontractor.id,
            "order_line": [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_qty': 1.0,
            })],
        })
        po.button_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', bom_product.id)])
        self.assertEqual(mo.picking_type_id, self.warehouse.subcontracting_type_id)

        delivery = po.picking_ids
        self.assertEqual(delivery.location_dest_id, super_subcontractor.property_stock_subcontractor)
        self.assertTrue(delivery.is_dropship)

        delivery.move_line_ids.quantity = 1.0
        delivery.move_ids.picked = True
        delivery.button_validate()

        self.assertEqual(po.order_line.qty_received, 1.0)

    def test_two_boms_same_component_supplier(self):
        """
        The "Dropship" route is modified: the propagation of the
        buy rule is set to "Leave Empty".
        Two subcontracted products (different subcontractor) that use the same
        component. The component has its own supplier. Confirm one PO for each
        subcontrated product. It should generate two PO from component's
        supplier to each subcontractor.
        """
        dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        dropship_route.rule_ids.filtered(lambda r: r.action == 'buy').group_propagation_option = 'none'

        subcontractor01, subcontractor02, component_supplier = self.env['res.partner'].create([{
            'name': 'Super Partner %d' % i
        } for i in range(3)])

        product01, product02, component = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': vendor.id})],
            'route_ids': [(6, 0, routes)],
        } for name, vendor, routes in [
            ('SuperProduct 01', subcontractor01, []),
            ('SuperProduct 02', subcontractor02, []),
            ('Component', component_supplier, dropship_route.ids),
        ]])

        self.env['mrp.bom'].create([{
            'product_tmpl_id': finished.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(4, subcontractor.id)],
            'bom_line_ids': [(0, 0, {'product_id': component.id})]
        } for finished, subcontractor in [
            (product01, subcontractor01),
            (product02, subcontractor02),
        ]])

        for (partner, product) in [(subcontractor01, product01), (subcontractor02, product02)]:
            po_form = Form(self.env['purchase.order'])
            po_form.partner_id = partner
            with po_form.order_line.new() as line:
                line.product_id = product
            po = po_form.save()
            po.button_confirm()

        supplier_orders = self.env['purchase.order'].search([('partner_id', '=', component_supplier.id)])
        self.assertEqual(supplier_orders.dest_address_id, subcontractor01 | subcontractor02)
        self.assertRecordValues(supplier_orders.order_line, [
            {'product_id': component.id, 'product_qty': 1.0},
            {'product_id': component.id, 'product_qty': 1.0},
        ])

    def test_subcontracted_bom_routes(self):
        """
        Take two BoM having those components. One being subcontracted and the other not.
         - Compo RR : Buy & Reordering rule to resupply subcontractor.
         - Compo DROP : Buy & Dropship.
        Check that depending on the context, the right route is shown on the report.
        """
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        dropship_route = self.env['stock.route'].search([('name', '=', 'Dropship')], limit=1)
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.manufacture_pull_id.route_id.write({'sequence': 20})

        compo_drop, compo_rr = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
            'seller_ids': [Command.create({'partner_id': self.subcontractor_partner1.parent_id.id})],
            'route_ids': [Command.set(routes)],
        } for name, routes in [
            ('Compo DROP', [route_buy.id, dropship_route.id]),
            ('Compo RR', [route_buy.id]),
        ]])

        route_resupply = self.env['stock.route'].search([('name', '=like', '%Resupply Subcontractor'), ('warehouse_ids', '=', warehouse.id)])
        route_resupply.product_selectable = True
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Resupply Subcontractor',
            'location_id': self.subcontractor_partner1.property_stock_subcontractor.id,
            'route_id': route_resupply.id,
            'product_id': compo_rr.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })
        compo_rr.route_ids = [Command.link(route_resupply.id)]

        bom_subcontract, bom_local = self.env['mrp.bom'].create([{
            'product_tmpl_id': self.comp1.product_tmpl_id.id,
            'type': bom_type,
            'subcontractor_ids': partner_id,
            'bom_line_ids': [
                Command.create({'product_id': compo_drop.id, 'product_qty': 1}),
                Command.create({'product_id': compo_rr.id, 'product_qty': 1}),
            ]
        } for bom_type, partner_id in [
            ('subcontract', [Command.link(self.subcontractor_partner1.id)]),
            ('normal', False),
        ]])
        # Need to add the subcontractor as Vendor to have the bom read as subcontracted.
        self.comp1.write({'seller_ids': [Command.create({'partner_id': self.subcontractor_partner1.id})]})

        report = self.env['report.mrp.report_bom_structure'].with_context(warehouse_id=warehouse.id)._get_report_data(bom_subcontract.id)
        component_lines = report.get('lines', []).get('components', [])
        self.assertEqual(component_lines[0]['product_id'], compo_drop.id)
        self.assertEqual(component_lines[0]['route_name'], 'Dropship')
        self.assertEqual(component_lines[1]['product_id'], compo_rr.id)
        self.assertEqual(component_lines[1]['route_name'], 'Buy', 'Despite the RR linked to it, it should still display the Buy route')

        report = self.env['report.mrp.report_bom_structure'].with_context(warehouse_id=warehouse.id)._get_report_data(bom_local.id)
        component_lines = report.get('lines', []).get('components', [])
        self.assertEqual(component_lines[0]['product_id'], compo_drop.id)
        self.assertEqual(component_lines[0]['route_name'], 'Buy', 'Outside of the subcontracted context, it should try to resupply stock.')
        self.assertEqual(component_lines[1]['product_id'], compo_rr.id)
        self.assertEqual(component_lines[1]['route_name'], 'Buy')

    def test_partner_id_no_overwrite(self):
        subcontract_location = self.env.company.subcontracting_location_id
        p1, p2 = self.env['res.partner'].create([
            {'name': 'partner 1', 'property_stock_subcontractor': subcontract_location.id},
            {'name': 'partner 2', 'property_stock_subcontractor': subcontract_location.id},
        ])
        route_resupply = self.env['stock.route'].create({
            'name': 'Resupply Subcontractor',
            'rule_ids': [(0, False, {
                'name': 'Stock -> Subcontractor',
                'location_src_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': subcontract_location.id,
                'company_id': self.env.company.id,
                'action': 'pull',
                'auto': 'manual',
                'picking_type_id': self.env.ref('stock.picking_type_out').id,
                'partner_address_id': p1.id,
            })],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Resupply Subcontractor',
            'location_id': subcontract_location.id,
            'route_id': route_resupply.id,
            'product_id': self.comp1.id,
            'product_min_qty': 2,
            'product_max_qty': 2,
        })
        self.env['procurement.group'].run_scheduler()
        delivery = self.env["stock.move"].search([("product_id", "=", self.comp1.id)]).picking_id
        self.assertEqual(delivery.partner_id, p1)


class TestSubcontractingDropshippingPortal(TestSubcontractingPortal):

    def test_portal_subcontractor_record_production_with_dropship(self):
        """
        Check that a portal subcontractor is able to set serial numbers for
        the final product (with a dropshipped component).
        """
        subcontractor, vendor = self.portal_user.partner_id | self.env['res.partner'].create([
            {'name': 'SuperVendor'},
        ])
        routes = self.env.ref('purchase_stock.route_warehouse0_buy') | self.env.ref('stock_dropshipping.route_drop_shipping')
        finished_product, component = self.env['product.product'].create([
            {
                'name': 'Robot',
                'is_storable': True,
                'tracking': 'serial',
                'seller_ids':[Command.create({'partner_id': subcontractor.id})],
            },
            {
                'name': 'Robot parts',
                'is_storable': True,
                'route_ids': [Command.set(routes.ids)],
                'seller_ids':[Command.create({'partner_id': vendor.id})],
            },
        ])
        bom_form = Form(self.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.subcontractor_ids.add(subcontractor)
        bom_form.product_tmpl_id = finished_product.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = component
            bom_line.product_qty = 1
        bom = bom_form.save()
        finished_serial = self.env['stock.lot'].create({
            'name': 'SN404',
            'product_id': finished_product.id,
        })
        po = self.env['purchase.order'].create({
            "partner_id": subcontractor.id,
            "dest_address_id": subcontractor.id,
            "order_line": [Command.create({
                'product_id': finished_product.id,
                'name': finished_product.name,
                'product_qty': 2,
            })],
        })
        po.button_confirm()
        subcontracted_mo = self.env['mrp.production'].search([('bom_id', '=', bom.id)], limit=1)
        # confirm the po to resuply the subcontractor
        po_dropship_subcontractor = self.env['purchase.order'].search([('partner_id', '=', vendor.id)], limit=1)
        po_dropship_subcontractor.button_confirm()
        # check that the dropship is linked to the subcontracted MO
        self.assertEqual(po_dropship_subcontractor.picking_ids.picking_type_id, self.env.company.dropship_subcontractor_pick_type_id)
        self.assertEqual(po_dropship_subcontractor.picking_ids, subcontracted_mo.picking_ids)

        # check that your subcontractor is able to modify the lot of the finished product
        action = subcontracted_mo.incoming_picking.with_user(self.portal_user).with_context(is_subcontracting_portal=True).move_ids.action_show_details()
        mo = self.env['mrp.production'].with_user(self.portal_user).browse(action['res_id'])
        mo_form = Form(mo.with_context(action['context']), view=action['view_id'])
        # Registering components for the first manufactured product
        mo_form.lot_producing_id = finished_serial
        mo = mo_form.save()
        mo.subcontracting_record_component()
        self.assertRecordValues(mo, [{
            'qty_producing': 1.0, 'lot_producing_id': finished_serial.id, 'state': 'to_close',
        }])
        # Check that the initial MO has been splitted in 2
        self.assertTrue("-001" in mo.name)
        self.assertRecordValues(mo.procurement_group_id.mrp_production_ids - mo, [{
            'qty_producing': 1.0, 'lot_producing_id': False, 'state': 'to_close',
        }])

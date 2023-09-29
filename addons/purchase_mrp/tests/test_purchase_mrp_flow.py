# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form, TransactionCase
from odoo.tests import Form
from odoo import fields


class TestSaleMrpFlow(TransactionCase):

    def setUp(self):
        super(TestSaleMrpFlow, self).setUp()
        # Useful models
        self.UoM = self.env['uom.uom']
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('uom.product_uom_categ_kgm')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env.ref('stock.warehouse0')

        self.uom_kg = self.env['uom.uom'].search([('category_id', '=', self.categ_kgm.id), ('uom_type', '=', 'reference')],
                                                 limit=1)
        self.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001})
        self.uom_gm = self.UoM.create({
            'name': 'Test-G',
            'category_id': self.categ_kgm.id,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        self.uom_unit = self.env['uom.uom'].search(
            [('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 0.01})
        self.uom_dozen = self.UoM.create({
            'name': 'Test-DozenA',
            'category_id': self.categ_unit.id,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Creating all components
        self.component_a = self._create_product('Comp A', self.uom_unit)
        self.component_b = self._create_product('Comp B', self.uom_unit)
        self.component_c = self._create_product('Comp C', self.uom_unit)
        self.component_d = self._create_product('Comp D', self.uom_unit)
        self.component_e = self._create_product('Comp E', self.uom_unit)
        self.component_f = self._create_product('Comp F', self.uom_unit)
        self.component_g = self._create_product('Comp G', self.uom_unit)

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # kit_1 --|- component_a   x2
        #         |- component_b   x1
        #         |- component_c   x3

        self.kit_1 = self._create_product('Kit 1', self.uom_unit)

        self.bom_kit_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine = self.env['mrp.bom.line']
        BomLine.create({
            'product_id': self.component_a.id,
            'product_qty': 2.0,
            'bom_id': self.bom_kit_1.id})
        BomLine.create({
            'product_id': self.component_b.id,
            'product_qty': 1.0,
            'bom_id': self.bom_kit_1.id})
        BomLine.create({
            'product_id': self.component_c.id,
            'product_qty': 3.0,
            'bom_id': self.bom_kit_1.id})

        # Create a kit 'kit_parent' :
        # ---------------------------
        #
        # kit_parent --|- kit_2 x2 --|- component_d x1
        #              |             |- kit_1 x2 -------|- component_a   x2
        #              |                                |- component_b   x1
        #              |                                |- component_c   x3
        #              |
        #              |- kit_3 x1 --|- component_f x1
        #              |             |- component_g x2
        #              |
        #              |- component_e x1

        # Creating all kits
        self.kit_2 = self._create_product('Kit 2', self.uom_unit)
        self.kit_3 = self._create_product('kit 3', self.uom_unit)
        self.kit_parent = self._create_product('Kit Parent', self.uom_unit)

        # Linking the kits and the components via some 'phantom' BoMs
        bom_kit_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_d.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_2.id})
        BomLine.create({
            'product_id': self.kit_1.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_2.id})

        bom_kit_parent = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_parent.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_e.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_parent.id})
        BomLine.create({
            'product_id': self.kit_2.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

        bom_kit_3 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_3.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': self.component_f.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_3.id})
        BomLine.create({
            'product_id': self.component_g.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_3.id})

        BomLine.create({
            'product_id': self.kit_3.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

    def _create_product(self, name, uom_id, routes=()):
        p = Form(self.env['product.product'])
        p.name = name
        p.type = 'product'
        p.uom_id = uom_id
        p.uom_po_id = uom_id
        p.route_ids.clear()
        for r in routes:
            p.route_ids.add(r)
        return p.save()

        # Helper to process quantities based on a dict following this structure :
        #
        # qty_to_process = {
        #     product_id: qty
        # }

    def _process_quantities(self, moves, quantities_to_process):
        """ Helper to process quantities based on a dict following this structure :
            qty_to_process = {
                product_id: qty
            }
        """
        moves_to_process = moves.filtered(lambda m: m.product_id in quantities_to_process.keys())
        for move in moves_to_process:
            move.write({'quantity_done': quantities_to_process[move.product_id]})

    def _assert_quantities(self, moves, quantities_to_process):
        """ Helper to check expected quantities based on a dict following this structure :
            qty_to_process = {
                product_id: qty
                ...
            }
        """
        moves_to_process = moves.filtered(lambda m: m.product_id in quantities_to_process.keys())
        for move in moves_to_process:
            self.assertEqual(move.product_uom_qty, quantities_to_process[move.product_id])

    def _create_move_quantities(self, qty_to_process, components, warehouse):
        """ Helper to creates moves in order to update the quantities of components
        on a specific warehouse. This ensure that all compute fields are triggered.
        The structure of qty_to_process should be the following :

         qty_to_process = {
            component: (qty, uom),
            ...
        }
        """
        for comp in components:
            f = Form(self.env['stock.move'])
            f.name = 'Test Receipt Components'
            f.location_id = self.env.ref('stock.stock_location_suppliers')
            f.location_dest_id = warehouse.lot_stock_id
            f.product_id = comp
            f.product_uom = qty_to_process[comp][1]
            f.product_uom_qty = qty_to_process[comp][0]
            move = f.save()
            move._action_confirm()
            move._action_assign()
            move_line = move.move_line_ids[0]
            move_line.qty_done = qty_to_process[comp][0]
            move._action_done()

    def test_01_sale_mrp_kit_qty_delivered(self):
        """ Test that the quantities delivered are correct when
        a kit with subkits is ordered with multiple backorders and returns
        """

        # 'kit_parent' structure:
        # ---------------------------
        #
        # kit_parent --|- kit_2 x2 --|- component_d x1
        #              |             |- kit_1 x2 -------|- component_a   x2
        #              |                                |- component_b   x1
        #              |                                |- component_c   x3
        #              |
        #              |- kit_3 x1 --|- component_f x1
        #              |             |- component_g x2
        #              |
        #              |- component_e x1

        # Creation of a sale order for x7 kit_parent
        partner = self.env['res.partner'].create({'name': 'My Test Partner'})
        f = Form(self.env['purchase.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.kit_parent
            line.product_qty = 7.0
            line.price_unit = 10

        po = f.save()
        po.button_confirm()

        # Check picking creation, its move lines should concern
        # only components. Also checks that the quantities are corresponding
        # to the PO
        self.assertEqual(len(po.picking_ids), 1)
        order_line = po.order_line[0]
        picking_original = po.picking_ids[0]
        move_lines = picking_original.move_lines
        products = move_lines.mapped('product_id')
        kits = [self.kit_parent, self.kit_3, self.kit_2, self.kit_1]
        components = [self.component_a, self.component_b, self.component_c, self.component_d, self.component_e,
                      self.component_f, self.component_g]
        expected_quantities = {
            self.component_a: 56.0,
            self.component_b: 28.0,
            self.component_c: 84.0,
            self.component_d: 14.0,
            self.component_e: 7.0,
            self.component_f: 14.0,
            self.component_g: 28.0
        }

        self.assertEqual(len(move_lines), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_lines, expected_quantities)

        # Process only 7 units of each component
        qty_to_process = 7
        move_lines.write({'quantity_done': qty_to_process})

        # Create a backorder for the missing componenents
        pick = po.picking_ids[0]
        res = pick.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check that a backorded is created
        self.assertEqual(len(po.picking_ids), 2)
        backorder_1 = po.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        # Even if some components are received completely,
        # no KitParent should be received
        self.assertEqual(order_line.qty_received, 0)

        # Process just enough components to make 1 kit_parent
        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_lines, qty_to_process)

        # Create a backorder for the missing componenents
        res = backorder_1.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Only 1 kit_parent should be received at this point
        self.assertEqual(order_line.qty_received, 1)

        # Check that the second backorder is created
        self.assertEqual(len(po.picking_ids), 3)
        backorder_2 = po.picking_ids - picking_original - backorder_1
        self.assertEqual(backorder_2.backorder_id.id, backorder_1.id)

        # Set the components quantities that backorder_2 should have
        expected_quantities = {
            self.component_a: 48,
            self.component_b: 21,
            self.component_c: 72,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 21
        }

        # Check that the computed quantities are matching the theorical ones.
        # Since component_e was totally processed, this componenent shouldn't be
        # present in backorder_2
        self.assertEqual(len(backorder_2.move_lines), 6)
        move_comp_e = backorder_2.move_lines.filtered(lambda m: m.product_id.id == self.component_e.id)
        self.assertFalse(move_comp_e)
        self._assert_quantities(backorder_2.move_lines, expected_quantities)

        # Process enough components to make x3 kit_parents
        qty_to_process = {
            self.component_a: 16,
            self.component_b: 5,
            self.component_c: 24,
            self.component_g: 5
        }
        self._process_quantities(backorder_2.move_lines, qty_to_process)

        # Create a backorder for the missing componenents
        res = backorder_2.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check that x3 kit_parents are indeed received
        self.assertEqual(order_line.qty_received, 3)

        # Check that the third backorder is created
        self.assertEqual(len(po.picking_ids), 4)
        backorder_3 = po.picking_ids - (picking_original + backorder_1 + backorder_2)
        self.assertEqual(backorder_3.backorder_id.id, backorder_2.id)

        # Check the components quantities that backorder_3 should have
        expected_quantities = {
            self.component_a: 32,
            self.component_b: 16,
            self.component_c: 48,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 16
        }
        self._assert_quantities(backorder_3.move_lines, expected_quantities)

        # Process all missing components
        self._process_quantities(backorder_3.move_lines, expected_quantities)

        # Validating the last backorder now it's complete.
        # All kits should be received
        backorder_3.button_validate()
        self.assertEqual(order_line.qty_received, 7.0)

        # Return all components processed by backorder_3
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=backorder_3.ids, active_id=backorder_3.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': expected_quantities[return_move.product_id],
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components and validate the picking
        wiz_act = return_pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # Now quantity received should be 3 again
        self.assertEqual(order_line.qty_received, 3)

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_pick.ids, active_id=return_pick.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for move in return_wiz.product_return_moves:
            move.quantity = expected_quantities[move.product_id]
        res = return_wiz.create_returns()
        return_of_return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components except one of each
        for move in return_of_return_pick.move_lines:
            move.write({
                'quantity_done': expected_quantities[move.product_id] - 1,
                'to_refund': True
            })

        wiz_act = return_of_return_pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # As one of each component is missing, only 6 kit_parents should be received
        self.assertEqual(order_line.qty_received, 6)

        # Check that the 4th backorder is created.
        self.assertEqual(len(po.picking_ids), 7)
        backorder_4 = po.picking_ids - (
                    picking_original + backorder_1 + backorder_2 + backorder_3 + return_of_return_pick + return_pick)
        self.assertEqual(backorder_4.backorder_id.id, return_of_return_pick.id)

        # Check the components quantities that backorder_4 should have
        for move in backorder_4.move_lines:
            self.assertEqual(move.product_qty, 1)

    def test_concurent_procurements(self):
        """ Check a production created to fulfill a procurement will not
        replenish more that needed if others procurements have the same products
        than the production component. """

        warehouse = self.env.ref('stock.warehouse0')
        buy_route = warehouse.buy_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id

        vendor1 = self.env['res.partner'].create({'name': 'aaa', 'email': 'from.test@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': vendor1.id,
            'price': 50,
        })

        component = self.env['product.product'].create({
            'name': 'component',
            'type': 'product',
            'route_ids': [(4, buy_route.id)],
            'seller_ids': [(6, 0, [supplier_info1.id])],
        })
        finished = self.env['product.product'].create({
            'name': 'finished',
            'type': 'product',
            'route_ids': [(4, manufacture_route.id)],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'A RR',
            'location_id': warehouse.lot_stock_id.id,
            'product_id': component.id,
            'route_id': buy_route.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'A RR',
            'location_id': warehouse.lot_stock_id.id,
            'product_id': finished.id,
            'route_id': manufacture_route.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
        })

        self.env['mrp.bom'].create({
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ]})

        # Delivery to trigger replenishment
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = warehouse.out_type_id
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = finished
            move.product_uom_qty = 3
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = component
            move.product_uom_qty = 2
        picking = picking_form.save()
        picking.action_confirm()

        # Find PO
        purchase = self.env['purchase.order.line'].search([
            ('product_id', '=', component.id),
        ]).order_id
        self.assertTrue(purchase)
        self.assertEqual(purchase.order_line.product_qty, 5)

    def test_01_purchase_mrp_kit_qty_change(self):
        self.partner = self.env.ref('base.res_partner_1')

        # Create a PO with one unit of the kit product
        self.po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.kit_1.name, 'product_id': self.kit_1.id, 'product_qty': 1, 'product_uom': self.kit_1.uom_id.id, 'price_unit': 60.0, 'date_planned': fields.Datetime.now()})],
        })
        # Validate the PO
        self.po.button_confirm()

        # Check the component qty in the created picking
        self.assertEqual(self.po.picking_ids.move_ids_without_package[0].product_uom_qty,2, "The quantity of components must be created according to the BOM")
        self.assertEqual(self.po.picking_ids.move_ids_without_package[1].product_uom_qty,1, "The quantity of components must be created according to the BOM")
        self.assertEqual(self.po.picking_ids.move_ids_without_package[2].product_uom_qty,3, "The quantity of components must be created according to the BOM")

        # Update the kit quantity in the PO
        self.po.order_line[0].product_qty = 2
        # Check the component qty after the update
        self.assertEqual(self.po.picking_ids.move_ids_without_package[0].product_uom_qty,4, "The amount of the kit components must be updated when changing the quantity of the kit.")
        self.assertEqual(self.po.picking_ids.move_ids_without_package[1].product_uom_qty,2, "The amount of the kit components must be updated when changing the quantity of the kit.")
        self.assertEqual(self.po.picking_ids.move_ids_without_package[2].product_uom_qty,6, "The amount of the kit components must be updated when changing the quantity of the kit.")

    def test_procurement_with_preferred_route(self):
        """
        3-steps receipts. Suppose a product that has both buy and manufacture
        routes. The user runs an orderpoint with the preferred route defined to
        "Buy". A purchase order should be generated.
        """
        self.warehouse.reception_steps = 'three_steps'

        manu_route = self.warehouse.manufacture_pull_id.route_id
        buy_route = self.warehouse.buy_pull_id.route_id

        # un-prioritize the buy rules
        self.env['stock.rule'].search([]).sequence = 1
        buy_route.rule_ids.sequence = 2

        vendor = self.env['res.partner'].create({'name': 'super vendor'})

        product = self.env['product.product'].create({
            'name': 'super product',
            'type': 'product',
            'seller_ids': [(0, 0, {'name': vendor.id})],
            'route_ids': [(4, manu_route.id), (4, buy_route.id)],
        })

        rr = self.env['stock.warehouse.orderpoint'].create({
            'name': product.name,
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': product.id,
            'product_min_qty': 1,
            'product_max_qty': 1,
            'route_id': buy_route.id,
        })
        rr.action_replenish()

        move_stock, move_check = self.env['stock.move'].search([('product_id', '=', product.id)])

        self.assertRecordValues(move_check | move_stock, [
            {'location_id': self.warehouse.wh_input_stock_loc_id.id, 'location_dest_id': self.warehouse.wh_qc_stock_loc_id.id, 'state': 'waiting', 'move_dest_ids': move_stock.ids},
            {'location_id': self.warehouse.wh_qc_stock_loc_id.id, 'location_dest_id': self.warehouse.lot_stock_id.id, 'state': 'waiting', 'move_dest_ids': []},
        ])

        po = self.env['purchase.order'].search([('partner_id', '=', vendor.id)])
        self.assertTrue(po)

        po.button_confirm()
        move_in = po.picking_ids.move_lines
        self.assertEqual(move_in.move_dest_ids.ids, move_check.ids)

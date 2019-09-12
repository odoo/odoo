# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import common, Form
from odoo.exceptions import UserError
from odoo.tools import mute_logger, float_compare


# these tests create accounting entries, and therefore need a chart of accounts
@common.tagged('post_install', '-at_install')
class TestSaleMrpFlow(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestSaleMrpFlow, cls).setUpClass()
        # Useful models
        cls.StockMove = cls.env['stock.move']
        cls.UoM = cls.env['uom.uom']
        cls.MrpProduction = cls.env['mrp.production']
        cls.Inventory = cls.env['stock.inventory']
        cls.InventoryLine = cls.env['stock.inventory.line']
        cls.ProductProduce = cls.env['mrp.product.produce']
        cls.ProductCategory = cls.env['product.category']

        cls.categ_unit = cls.env.ref('uom.product_uom_categ_unit')
        cls.categ_kgm = cls.env.ref('uom.product_uom_categ_kgm')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.warehouse = cls.env.ref('stock.warehouse0')

        cls.uom_kg = cls.env['uom.uom'].search([('category_id', '=', cls.categ_kgm.id), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001})
        cls.uom_gm = cls.UoM.create({
            'name': 'Test-G',
            'category_id': cls.categ_kgm.id,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        cls.uom_unit = cls.env['uom.uom'].search([('category_id', '=', cls.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 0.01})
        cls.uom_dozen = cls.UoM.create({
            'name': 'Test-DozenA',
            'category_id': cls.categ_unit.id,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Creating all components
        cls.component_a = cls._cls_create_product('Comp A', cls.uom_unit)
        cls.component_b = cls._cls_create_product('Comp B', cls.uom_unit)
        cls.component_c = cls._cls_create_product('Comp C', cls.uom_unit)
        cls.component_d = cls._cls_create_product('Comp D', cls.uom_unit)
        cls.component_e = cls._cls_create_product('Comp E', cls.uom_unit)
        cls.component_f = cls._cls_create_product('Comp F', cls.uom_unit)
        cls.component_g = cls._cls_create_product('Comp G', cls.uom_unit)

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # kit_1 --|- component_a   x2
        #         |- component_b   x1
        #         |- component_c   x3

        cls.kit_1 = cls._cls_create_product('Kit 1', cls.uom_unit)

        cls.bom_kit_1 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine = cls.env['mrp.bom.line']
        BomLine.create({
            'product_id': cls.component_a.id,
            'product_qty': 2.0,
            'bom_id': cls.bom_kit_1.id})
        BomLine.create({
            'product_id': cls.component_b.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_kit_1.id})
        BomLine.create({
            'product_id': cls.component_c.id,
            'product_qty': 3.0,
            'bom_id': cls.bom_kit_1.id})

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
        cls.kit_2 = cls._cls_create_product('Kit 2', cls.uom_unit)
        cls.kit_3 = cls._cls_create_product('kit 3', cls.uom_unit)
        cls.kit_parent = cls._cls_create_product('Kit Parent', cls.uom_unit)

        # Linking the kits and the components via some 'phantom' BoMs
        bom_kit_2 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': cls.component_d.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_2.id})
        BomLine.create({
            'product_id': cls.kit_1.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_2.id})

        bom_kit_parent = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_parent.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': cls.component_e.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_parent.id})
        BomLine.create({
            'product_id': cls.kit_2.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

        bom_kit_3 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.kit_3.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': cls.component_f.id,
            'product_qty': 1.0,
            'bom_id': bom_kit_3.id})
        BomLine.create({
            'product_id': cls.component_g.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_3.id})

        BomLine.create({
            'product_id': cls.kit_3.id,
            'product_qty': 2.0,
            'bom_id': bom_kit_parent.id})

    @classmethod
    def _cls_create_product(cls, name, uom_id, routes=()):
        p = Form(cls.env['product.product'])
        p.name = name
        p.type = 'product'
        p.uom_id = uom_id
        p.uom_po_id = uom_id
        p.route_ids.clear()
        for r in routes:
            p.route_ids.add(r)
        return p.save()

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
            self.assertEquals(move.product_uom_qty, quantities_to_process[move.product_id])

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

    def test_00_sale_mrp_flow(self):
        """ Test sale to mrp flow with diffrent unit of measure."""


        # Create product A, B, C, D.
        # --------------------------
        route_manufacture = self.warehouse.manufacture_pull_id.route_id
        route_mto = self.warehouse.mto_pull_id.route_id
        product_a = self._create_product('Product A', self.uom_unit, routes=[route_manufacture, route_mto])
        product_c = self._create_product('Product C', self.uom_kg)
        product_b = self._create_product('Product B', self.uom_dozen, routes=[route_manufacture, route_mto])
        product_d = self._create_product('Product D', self.uom_unit, routes=[route_manufacture, route_mto])

        # ------------------------------------------------------------------------------------------
        # Bill of materials for product A, B, D.
        # ------------------------------------------------------------------------------------------

        # Bill of materials for Product A.
        with Form(self.env['mrp.bom']) as f:
            f.product_tmpl_id = product_a.product_tmpl_id
            f.product_qty = 2
            f.product_uom_id = self.uom_dozen
            with f.bom_line_ids.new() as line:
                line.product_id = product_b
                line.product_qty = 3
                line.product_uom_id = self.uom_unit
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 300.5
                line.product_uom_id = self.uom_gm
            with f.bom_line_ids.new() as line:
                line.product_id = product_d
                line.product_qty = 4
                line.product_uom_id = self.uom_unit

        # Bill of materials for Product B.
        with Form(self.env['mrp.bom']) as f:
            f.product_tmpl_id = product_b.product_tmpl_id
            f.product_qty = 1
            f.product_uom_id = self.uom_unit
            f.type = 'phantom'
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 0.400
                line.product_uom_id = self.uom_kg

        # Bill of materials for Product D.
        with Form(self.env['mrp.bom']) as f:
            f.product_tmpl_id = product_d.product_tmpl_id
            f.product_qty = 1
            f.product_uom_id = self.uom_unit
            with f.bom_line_ids.new() as line:
                line.product_id = product_c
                line.product_qty = 1
                line.product_uom_id = self.uom_kg

        # ----------------------------------------
        # Create sales order of 10 Dozen product A.
        # ----------------------------------------

        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.env.ref('base.res_partner_2')
        with order_form.order_line.new() as line:
            line.product_id = product_a
            line.product_uom = self.uom_dozen
            line.product_uom_qty = 10
        order = order_form.save()
        order.action_confirm()

        # ===============================================================================
        #  Sales order of 10 Dozen product A should create production order
        #  like ..
        # ===============================================================================
        #    Product A  10 Dozen.
        #        Product C  6 kg
        #                As product B phantom in bom A, product A will consume product C
        #                ================================================================
        #                For 1 unit product B it will consume 400 gm
        #                then for 15 unit (Product B 3 unit per 2 Dozen product A)
        #                product B it will consume [ 6 kg ] product C)
        #                Product A will consume 6 kg product C.
        #
        #                [15 * 400 gm ( 6 kg product C)] = 6 kg product C
        #
        #        Product C  1502.5 gm.
        #                [
        #                  For 2 Dozen product A will consume 300.5 gm product C
        #                  then for 10 Dozen product A will consume 1502.5 gm product C.
        #                ]
        #
        #        product D  20 Unit.
        #                [
        #                  For 2 dozen product A will consume 4 unit product D
        #                  then for 10 Dozen product A will consume 20 unit of product D.
        #                ]
        # --------------------------------------------------------------------------------

        # <><><><><><><><><><><><><><><><><><><><>
        # Check manufacturing order for product A.
        # <><><><><><><><><><><><><><><><><><><><>

        # Check quantity, unit of measure and state of manufacturing order.
        # -----------------------------------------------------------------
        self.env['procurement.group'].run_scheduler()
        mnf_product_a = self.env['mrp.production'].search([('product_id', '=', product_a.id)])

        self.assertTrue(mnf_product_a, 'Manufacturing order not created.')
        self.assertEqual(mnf_product_a.product_qty, 120, 'Wrong product quantity in manufacturing order.')
        self.assertEqual(mnf_product_a.product_uom_id, self.uom_unit, 'Wrong unit of measure in manufacturing order.')
        self.assertEqual(mnf_product_a.state, 'confirmed', 'Manufacturing order should be confirmed.')

        # ------------------------------------------------------------------------------------------
        # Check 'To consume line' for production order of product A.
        # ------------------------------------------------------------------------------------------

        # Check 'To consume line' with product c and uom kg.
        # -------------------------------------------------

        moves = self.StockMove.search([
            ('raw_material_production_id', '=', mnf_product_a.id),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_kg.id)])

        # Check total consume line with product c and uom kg.
        self.assertEqual(len(moves), 1, 'Production move lines are not generated proper.')
        list_qty = {move.product_uom_qty for move in moves}
        self.assertEqual(list_qty, {6.0}, "Wrong product quantity in 'To consume line' of manufacturing order.")
        # Check state of consume line with product c and uom kg.
        for move in moves:
            self.assertEqual(move.state, 'confirmed', "Wrong state in 'To consume line' of manufacturing order.")

        # Check 'To consume line' with product c and uom gm.
        # ---------------------------------------------------

        move = self.StockMove.search([
            ('raw_material_production_id', '=', mnf_product_a.id),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_gm.id)])

        # Check total consume line of product c with gm.
        self.assertEqual(len(move), 1, 'Production move lines are not generated proper.')
        # Check quantity should be with 1502.5 ( 2 Dozen product A consume 300.5 gm then 10 Dozen (300.5 * (10/2)).
        self.assertEqual(move.product_uom_qty, 1502.5, "Wrong product quantity in 'To consume line' of manufacturing order.")
        # Check state of consume line with product c with and uom gm.
        self.assertEqual(move.state, 'confirmed', "Wrong state in 'To consume line' of manufacturing order.")

        # Check 'To consume line' with product D.
        # ---------------------------------------

        move = self.StockMove.search([
            ('raw_material_production_id', '=', mnf_product_a.id),
            ('product_id', '=', product_d.id)])

        # Check total consume line with product D.
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')

        # <><><><><><><><><><><><><><><><><><><><><><>
        # Manufacturing order for product D (20 unit).
        # <><><><><><><><><><><><><><><><><><><><><><>

        # FP Todo: find a better way to look for the production order
        mnf_product_d = self.MrpProduction.search([('product_id', '=', product_d.id)], order='id desc', limit=1)
        # Check state of production order D.
        self.assertEqual(mnf_product_d.state, 'confirmed', 'Manufacturing order should be confirmed.')

        # Check 'To consume line' state, quantity, uom of production order (product D).
        # -----------------------------------------------------------------------------

        move = self.StockMove.search([('raw_material_production_id', '=', mnf_product_d.id), ('product_id', '=', product_c.id)])
        self.assertEqual(move.product_uom_qty, 20, "Wrong product quantity in 'To consume line' of manufacturing order.")
        self.assertEqual(move.product_uom.id, self.uom_kg.id, "Wrong unit of measure in 'To consume line' of manufacturing order.")
        self.assertEqual(move.state, 'confirmed', "Wrong state in 'To consume line' of manufacturing order.")

        # -------------------------------
        # Create inventory for product c.
        # -------------------------------
        # Need 20 kg product c to produce 20 unit product D.
        # --------------------------------------------------

        inventory = self.Inventory.create({
            'name': 'Inventory Product KG',
            'product_ids': [(4, product_c.id)]})

        inventory.action_start()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 20,
            'location_id': self.stock_location.id})
        inventory.action_validate()

        # --------------------------------------------------
        # Assign product c to manufacturing order of product D.
        # --------------------------------------------------

        mnf_product_d.action_assign()
        self.assertEqual(mnf_product_d.reservation_state, 'assigned', 'Availability should be assigned')
        self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # ------------------
        # produce product D.
        # ------------------

        produce_form = Form(self.ProductProduce.with_context({
            'active_id': mnf_product_d.id,
            'active_ids': [mnf_product_d.id],
        }))
        produce_form.qty_producing = 20
        produce_d = produce_form.save()
        # produce_d.on_change_qty()
        produce_d.do_produce()
        mnf_product_d.post_inventory()

        # Check state of manufacturing order.
        self.assertEqual(mnf_product_d.state, 'done', 'Manufacturing order should still be in progress state.')
        # Check available quantity of product D.
        self.assertEqual(product_d.qty_available, 20, 'Wrong quantity available of product D.')

        # -----------------------------------------------------------------
        # Check product D assigned or not to production order of product A.
        # -----------------------------------------------------------------

        self.assertEqual(mnf_product_a.state, 'confirmed', 'Manufacturing order should be confirmed.')
        move = self.StockMove.search([('raw_material_production_id', '=', mnf_product_a.id), ('product_id', '=', product_d.id)])
        self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # Create inventory for product C.
        # ------------------------------
        # Need product C ( 20 kg + 6 kg + 1502.5 gm = 27.5025 kg)
        # -------------------------------------------------------
        inventory = self.Inventory.create({
            'name': 'Inventory Product C KG',
            'product_ids': [(4, product_c.id)]})

        inventory.action_start()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 27.5025,
            'location_id': self.stock_location.id})
        inventory.action_validate()

        # Assign product to manufacturing order of product A.
        # ---------------------------------------------------

        mnf_product_a.action_assign()
        self.assertEqual(mnf_product_a.reservation_state, 'assigned', 'Manufacturing order inventory state should be available.')
        moves = self.StockMove.search([('raw_material_production_id', '=', mnf_product_a.id), ('product_id', '=', product_c.id)])

        # Check product c move line state.
        for move in moves:
            self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # Produce product A.
        # ------------------

        produce_form = Form(self.ProductProduce.with_context({
            'active_id': mnf_product_a.id,
            'active_ids': [mnf_product_a.id],
        }))
        produce_a = produce_form.save()
        produce_a.do_produce()
        mnf_product_a.post_inventory()
        # Check state of manufacturing order product A.
        self.assertEqual(mnf_product_a.state, 'done', 'Manufacturing order should still be in the progress state.')
        # Check product A avaialble quantity should be 120.
        self.assertEqual(product_a.qty_available, 120, 'Wrong quantity available of product A.')

    def test_01_sale_mrp_delivery_kit(self):
        """ Test delivered quantity on SO based on delivered quantity in pickings."""
        # intial so
        product = self.env.ref('mrp.product_product_table_kit')
        product.type = 'consu'
        product.invoice_policy = 'delivery'
        # Remove the MTO route as purchase is not installed and since the procurement removal the exception is directly raised
        product.write({'route_ids': [(6, 0, [self.warehouse.manufacture_pull_id.route_id.id])]})

        partner = self.env.ref('base.res_partner_1')
        # if `delivery` module is installed, a default property is set for the carrier to use
        # However this will lead to an extra line on the SO (the delivery line), which will force
        # the SO to have a different flow (and `invoice_state` value)
        partner.property_delivery_carrier_id = False

        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 5
        so = f.save()

        # confirm our standard so, check the picking
        so.action_confirm()
        self.assertTrue(so.picking_ids, 'Sale MRP: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        with self.assertRaises(UserError):
            so._create_invoices()
        self.assertEqual(so.invoice_status, 'no', 'Sale MRP: so invoice_status should be "nothing to invoice" after invoicing')

        # deliver partially (1 of each instead of 5), check the so's invoice_status and delivered quantities
        pick = so.picking_ids
        pick.move_lines.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        self.assertEqual(so.invoice_status, 'no', 'Sale MRP: so invoice_status should be "no" after partial delivery of a kit')
        del_qty = sum(sol.qty_delivered for sol in so.order_line)
        self.assertEqual(del_qty, 0.0, 'Sale MRP: delivered quantity should be zero after partial delivery of a kit')
        # deliver remaining products, check the so's invoice_status and delivered quantities
        self.assertEqual(len(so.picking_ids), 2, 'Sale MRP: number of pickings should be 2')
        pick_2 = so.picking_ids.filtered('backorder_id')
        for move in pick_2.move_lines:
            if move.product_id.id == self.env.ref('mrp.product_product_computer_desk_bolt').id:
                move.write({'quantity_done': 19})
            else:
                move.write({'quantity_done': 4})
        pick_2.button_validate()

        del_qty = sum(sol.qty_delivered for sol in so.order_line)
        self.assertEqual(del_qty, 5.0, 'Sale MRP: delivered quantity should be 5.0 after complete delivery of a kit')
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale MRP: so invoice_status should be "to invoice" after complete delivery of a kit')

    def test_02_sale_mrp_anglo_saxon(self):
        """Test the price unit of a kit"""
        # This test will check that the correct journal entries are created when a stockable product in real time valuation
        # and in fifo cost method is sold in a company using anglo-saxon.
        # For this test, let's consider a product category called Test category in real-time valuation and real price costing method
        # Let's  also consider a finished product with a bom with two components: component1(cost = 20) and component2(cost = 10)
        # These products are in the Test category
        # The bom consists of 2 component1 and 1 component2
        # The invoice policy of the finished product is based on delivered quantities
        self.env.company.currency_id = self.env.ref('base.USD')
        self.uom_unit = self.UoM.create({
            'name': 'Test-Unit',
            'category_id': self.categ_unit.id,
            'factor': 1,
            'uom_type': 'bigger',
            'rounding': 1.0})
        self.company = self.env.ref('base.main_company')
        self.company.anglo_saxon_accounting = True
        self.partner = self.env.ref('base.res_partner_1')
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category','property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_type = self.env['account.account.type'].create({'name': 'RCV type', 'type': 'other', 'internal_group': 'asset'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_valuation = self.env['account.account'].create({'name': 'Valuation', 'code': 'STV00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = self.account_receiv
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = self.account_receiv
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = account_valuation
        self.category.property_stock_journal = self.env['account.journal'].create({'name': 'Stock journal', 'type': 'sale', 'code': 'STK00'})

        Product = self.env['product.product']
        self.finished_product = Product.create({
                'name': 'Finished product',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'delivery',
                'categ_id': self.category.id})
        self.component1 = Product.create({
                'name': 'Component 1',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'standard_price': 20})
        self.component2 = Product.create({
                'name': 'Component 2',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'standard_price': 10})
        self.env['stock.quant'].create({
            'product_id': self.component1.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 6.0,
        })
        self.env['stock.quant'].create({
            'product_id': self.component2.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 3.0,
        })
        self.bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.finished_product.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'phantom'})
        BomLine = self.env['mrp.bom.line']
        BomLine.create({
                'product_id': self.component1.id,
                'product_qty': 2.0,
                'bom_id': self.bom.id})
        BomLine.create({
                'product_id': self.component2.id,
                'product_qty': 1.0,
                'bom_id': self.bom.id})

        # Create a SO for a specific partner for three units of the finished product
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.finished_product.name,
                'product_id': self.finished_product.id,
                'product_uom_qty': 3,
                'product_uom': self.finished_product.uom_id.id,
                'price_unit': self.finished_product.list_price
            })],
            'pricelist_id': self.env.ref('product.list0').id,
            'company_id': self.company.id,
        }
        self.so = self.env['sale.order'].create(so_vals)
        # Validate the SO
        self.so.action_confirm()
        # Deliver the three finished products
        pick = self.so.picking_ids
        # To check the products on the picking
        self.assertEqual(pick.move_lines.mapped('product_id'), self.component1 | self.component2)
        wiz_act = pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        # Create the invoice
        self.so._create_invoices()
        self.invoice = self.so.invoice_ids
        # Changed the invoiced quantity of the finished product to 2
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        self.invoice = move_form.save()
        self.invoice.post()
        aml = self.invoice.line_ids
        aml_expense = aml.filtered(lambda l: l.is_anglo_saxon_line and l.debit > 0)
        aml_output = aml.filtered(lambda l: l.is_anglo_saxon_line and l.credit > 0)
        # Check that the cost of Good Sold entries are equal to 2* (2 * 20 + 1 * 10) = 100
        self.assertEqual(aml_expense.debit, 100, "Cost of Good Sold entry missing or mismatching")
        self.assertEqual(aml_output.credit, 100, "Cost of Good Sold entry missing or mismatching")

    def test_03_sale_mrp_simple_kit_qty_delivered(self):
        """ Test that the quantities delivered are correct when
        a simple kit is ordered with multiple backorders
        """

        # kit_1 structure:
        # ================

        # kit_1 ---|- component_a  x2
        #          |- component_b  x1
        #          |- component_c  x3

        # Updating the quantities in stock to prevent
        # a 'Not enough inventory' warning message.
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 20)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_c, stock_location, 30)

        # Creation of a sale order for x10 kit_1
        partner = self.env.ref('base.res_partner_1')
        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.kit_1
            line.product_uom_qty = 10.0

        # Confirming the SO to trigger the picking creation
        so = f.save()
        so.action_confirm()

        # Check picking creation
        self.assertEquals(len(so.picking_ids), 1)
        picking_original = so.picking_ids[0]
        move_lines = picking_original.move_lines

        # Check if the correct amount of stock.moves are created
        self.assertEquals(len(move_lines), 3)

        # Check if BoM is created and is for a 'Kit'
        bom_from_k1 = self.env['mrp.bom']._bom_find(product=self.kit_1)
        self.assertEquals(self.bom_kit_1.id, bom_from_k1.id)
        self.assertEquals(bom_from_k1.type, 'phantom')

        # Check there's only 1 order line on the SO and it's for x10 'kit_1'
        order_lines = so.order_line
        self.assertEquals(len(order_lines), 1)
        order_line = order_lines[0]
        self.assertEquals(order_line.product_id.id, self.kit_1.id)
        self.assertEquals(order_line.product_uom_qty, 10.0)

        # Check if correct qty is ordered for each component of the kit
        expected_quantities = {
            self.component_a: 20,
            self.component_b: 10,
            self.component_c: 30,
        }
        self._assert_quantities(move_lines, expected_quantities)

        # Process only x1 of the first component then create a backorder for the missing components
        picking_original.move_lines.sorted()[0].write({'quantity_done': 1})
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, so.picking_ids[0].id)]})
        backorder_wizard.process()

        # Check that the backorder was created, no kit should be delivered at this point
        self.assertEquals(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEquals(backorder_1.backorder_id.id, picking_original.id)
        self.assertEquals(order_line.qty_delivered, 0)

        # Process only x6 each componenent in the picking
        # Then create a backorder for the missing components
        backorder_1.move_lines.write({'quantity_done': 6})
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_1.id)]})
        backorder_wizard.process()

        # Check that a backorder is created
        self.assertEquals(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
        self.assertEquals(backorder_2.backorder_id.id, backorder_1.id)

        # With x6 unit of each components, we can only make 2 kits.
        # So only 2 kits should be delivered
        self.assertEquals(order_line.qty_delivered, 2)

        # Process x3 more unit of each components :
        # - Now only 3 kits should be delivered
        # - A backorder will be created, the SO should have 3 picking_ids linked to it.
        backorder_2.move_lines.write({'quantity_done': 3})

        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_2.id)]})
        backorder_wizard.process()

        self.assertEquals(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - picking_original - backorder_2 - backorder_1
        self.assertEquals(backorder_3.backorder_id.id, backorder_2.id)
        self.assertEquals(order_line.qty_delivered, 3)

        # Adding missing components
        qty_to_process = {
            self.component_a: 10,
            self.component_b: 1,
            self.component_c: 21,
        }
        self._process_quantities(backorder_3.move_lines, qty_to_process)

        # Validating the last backorder now it's complete
        backorder_3.button_validate()
        order_line._compute_qty_delivered()

        # All kits should be delivered
        self.assertEquals(order_line.qty_delivered, 10)

    def test_04_sale_mrp_kit_qty_delivered(self):
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

        # Updating the quantities in stock to prevent
        # a 'Not enough inventory' warning message.
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 56)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 28)
        self.env['stock.quant']._update_available_quantity(self.component_c, stock_location, 84)
        self.env['stock.quant']._update_available_quantity(self.component_d, stock_location, 14)
        self.env['stock.quant']._update_available_quantity(self.component_e, stock_location, 7)
        self.env['stock.quant']._update_available_quantity(self.component_f, stock_location, 14)
        self.env['stock.quant']._update_available_quantity(self.component_g, stock_location, 28)

        # Creation of a sale order for x7 kit_parent
        partner = self.env.ref('base.res_partner_1')
        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.kit_parent
            line.product_uom_qty = 7.0

        so = f.save()
        so.action_confirm()

        # Check picking creation, its move lines should concern
        # only components. Also checks that the quantities are corresponding
        # to the SO
        self.assertEquals(len(so.picking_ids), 1)
        order_line = so.order_line[0]
        picking_original = so.picking_ids[0]
        move_lines = picking_original.move_lines
        products = move_lines.mapped('product_id')
        kits = [self.kit_parent, self.kit_3, self.kit_2, self.kit_1]
        components = [self.component_a, self.component_b, self.component_c, self.component_d, self.component_e, self.component_f, self.component_g]
        expected_quantities = {
            self.component_a: 56.0,
            self.component_b: 28.0,
            self.component_c: 84.0,
            self.component_d: 14.0,
            self.component_e: 7.0,
            self.component_f: 14.0,
            self.component_g: 28.0
        }

        self.assertEquals(len(move_lines), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_lines, expected_quantities)

        # Process only 7 units of each component
        qty_to_process = 7
        move_lines.write({'quantity_done': qty_to_process})

        # Create a backorder for the missing componenents
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, so.picking_ids[0].id)]})
        backorder_wizard.process()

        # Check that a backorded is created
        self.assertEquals(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEquals(backorder_1.backorder_id.id, picking_original.id)

        # Even if some components are delivered completely,
        # no KitParent should be delivered
        self.assertEquals(order_line.qty_delivered, 0)

        # Process just enough components to make 1 kit_parent
        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_lines, qty_to_process)

        # Create a backorder for the missing componenents
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_1.id)]})
        backorder_wizard.process()

        # Only 1 kit_parent should be delivered at this point
        self.assertEquals(order_line.qty_delivered, 1)

        # Check that the second backorder is created
        self.assertEquals(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
        self.assertEquals(backorder_2.backorder_id.id, backorder_1.id)

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
        self.assertEquals(len(backorder_2.move_lines), 6)
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
        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, backorder_2.id)]})
        backorder_wizard.process()

        # Check that x3 kit_parents are indeed delivered
        self.assertEquals(order_line.qty_delivered, 3)

        # Check that the third backorder is created
        self.assertEquals(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - (picking_original + backorder_1 + backorder_2)
        self.assertEquals(backorder_3.backorder_id.id, backorder_2.id)

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
        # All kits should be delivered
        backorder_3.button_validate()
        self.assertEquals(order_line.qty_delivered, 7.0)

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
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        # Now quantity delivered should be 3 again
        self.assertEquals(order_line.qty_delivered, 3)

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

        backorder_wizard = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, return_of_return_pick.id)]})
        backorder_wizard.process()

        # As one of each component is missing, only 6 kit_parents should be delivered
        self.assertEquals(order_line.qty_delivered, 6)

        # Check that the 4th backorder is created.
        self.assertEquals(len(so.picking_ids), 7)
        backorder_4 = so.picking_ids - (picking_original + backorder_1 + backorder_2 + backorder_3 + return_of_return_pick + return_pick)
        self.assertEquals(backorder_4.backorder_id.id, return_of_return_pick.id)

        # Check the components quantities that backorder_4 should have
        for move in backorder_4.move_lines:
            self.assertEquals(move.product_qty, 1)

    @mute_logger('odoo.tests.common.onchange')
    def test_05_mrp_sale_kit_availability(self):
        """
        Check that the 'Not enough inventory' warning message shows correct
        informations when a kit is ordered
        """

        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1'
        })
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 2',
            'code': 'WH2'
        })

        # Those are all componenents needed to make kit_parents
        components = [self.component_a, self.component_b, self.component_c, self.component_d, self.component_e,
                      self.component_f, self.component_g]

        # Set enough quantities to make 1 kit_uom_in_kit in WH1
        self.env['stock.quant']._update_available_quantity(self.component_a, warehouse_1.lot_stock_id, 8)
        self.env['stock.quant']._update_available_quantity(self.component_b, warehouse_1.lot_stock_id, 4)
        self.env['stock.quant']._update_available_quantity(self.component_c, warehouse_1.lot_stock_id, 12)
        self.env['stock.quant']._update_available_quantity(self.component_d, warehouse_1.lot_stock_id, 2)
        self.env['stock.quant']._update_available_quantity(self.component_e, warehouse_1.lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(self.component_f, warehouse_1.lot_stock_id, 2)
        self.env['stock.quant']._update_available_quantity(self.component_g, warehouse_1.lot_stock_id, 4)

        # Set quantities on WH2, but not enough to make 1 kit_parent
        self.env['stock.quant']._update_available_quantity(self.component_a, warehouse_2.lot_stock_id, 7)
        self.env['stock.quant']._update_available_quantity(self.component_b, warehouse_2.lot_stock_id, 3)
        self.env['stock.quant']._update_available_quantity(self.component_c, warehouse_2.lot_stock_id, 12)
        self.env['stock.quant']._update_available_quantity(self.component_d, warehouse_2.lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(self.component_e, warehouse_2.lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(self.component_f, warehouse_2.lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(self.component_g, warehouse_2.lot_stock_id, 4)

        # Creation of a sale order for x7 kit_parent
        qty_ordered = 7
        f = Form(self.env['sale.order'])
        f.partner_id = self.env.ref('base.res_partner_1')
        f.warehouse_id = warehouse_2
        with f.order_line.new() as line:
            line.product_id = self.kit_parent
            line.product_uom_qty = qty_ordered
        so = f.save()
        order_line = so.order_line[0]

        # Check that not enough enough quantities are available in the warehouse set in the SO
        # but there are enough quantities in Warehouse 1 for 1 kit_parent
        kit_parent_wh_order = self.kit_parent.with_context(warehouse=so.warehouse_id.id)

        # Check that not enough enough quantities are available in the warehouse set in the SO
        # but there are enough quantities in Warehouse 1 for 1 kit_parent
        self.assertEquals(kit_parent_wh_order.virtual_available, 0)
        kit_parent_wh_order.invalidate_cache()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse=warehouse_1.id)
        self.assertEquals(kit_parent_wh1.virtual_available, 1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)

        # We receive enoug of each component in Warehouse 2 to make 3 kit_parent
        qty_to_process = {
            self.component_a: (17, self.uom_unit),
            self.component_b: (12, self.uom_unit),
            self.component_c: (25, self.uom_unit),
            self.component_d: (5, self.uom_unit),
            self.component_e: (2, self.uom_unit),
            self.component_f: (5, self.uom_unit),
            self.component_g: (8, self.uom_unit),
        }
        self._create_move_quantities(qty_to_process, components, warehouse_2)

        # As 'Warehouse 2' is the warehouse linked to the SO, 3 kits should be available
        # But the quantity available in Warehouse 1 should stay 1
        kit_parent_wh_order = self.kit_parent.with_context(warehouse=so.warehouse_id.id)
        self.assertEquals(kit_parent_wh_order.virtual_available, 3)
        kit_parent_wh_order.invalidate_cache()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse=warehouse_1.id)
        self.assertEquals(kit_parent_wh1.virtual_available, 1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)

        # We receive enough of each component in Warehouse 2 to make 7 kit_parent
        qty_to_process = {
            self.component_a: (32, self.uom_unit),
            self.component_b: (16, self.uom_unit),
            self.component_c: (48, self.uom_unit),
            self.component_d: (8, self.uom_unit),
            self.component_e: (4, self.uom_unit),
            self.component_f: (8, self.uom_unit),
            self.component_g: (16, self.uom_unit),
        }
        self._create_move_quantities(qty_to_process, components, warehouse_2)

        # Enough quantities should be available, no warning message should be displayed
        kit_parent_wh_order = self.kit_parent.with_context(warehouse=so.warehouse_id.id)
        self.assertEquals(kit_parent_wh_order.virtual_available, 7)

    def test_06_kit_qty_delivered_mixed_uom(self):
        """
        Check that the quantities delivered are correct when a kit involves
        multiple UoMs on its components
        """
        # Create some components
        component_uom_unit = self._create_product('Comp Unit', self.uom_unit)
        component_uom_dozen = self._create_product('Comp Dozen', self.uom_dozen)
        component_uom_kg = self._create_product('Comp Kg', self.uom_kg)

        # Create a kit 'kit_uom_1' :
        # -----------------------
        #
        # kit_uom_1 --|- component_uom_unit    x2 Test-Dozen
        #             |- component_uom_dozen   x1 Test-Dozen
        #             |- component_uom_kg      x3 Test-G

        kit_uom_1 = self._create_product('Kit 1', self.uom_unit)

        bom_kit_uom_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_uom_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine = self.env['mrp.bom.line']
        BomLine.create({
            'product_id': component_uom_unit.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_dozen.id,
            'bom_id': bom_kit_uom_1.id})
        BomLine.create({
            'product_id': component_uom_dozen.id,
            'product_qty': 1.0,
            'product_uom_id': self.uom_dozen.id,
            'bom_id': bom_kit_uom_1.id})
        BomLine.create({
            'product_id': component_uom_kg.id,
            'product_qty': 3.0,
            'product_uom_id': self.uom_gm.id,
            'bom_id': bom_kit_uom_1.id})

        # Updating the quantities in stock to prevent
        # a 'Not enough inventory' warning message.
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(component_uom_unit, stock_location, 240)
        self.env['stock.quant']._update_available_quantity(component_uom_dozen, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(component_uom_kg, stock_location, 0.03)

        # Creation of a sale order for x10 kit_1
        partner = self.env.ref('base.res_partner_1')
        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = kit_uom_1
            line.product_uom_qty = 10.0

        so = f.save()
        so.action_confirm()

        picking_original = so.picking_ids[0]
        move_lines = picking_original.move_lines
        order_line = so.order_line[0]

        # Check that the quantities on the picking are the one expected for each components
        for ml in move_lines:
            corr_bom_line = bom_kit_uom_1.bom_line_ids.filtered(lambda b: b.product_id.id == ml.product_id.id)
            computed_qty = ml.product_uom._compute_quantity(ml.product_uom_qty, corr_bom_line.product_uom_id)
            self.assertEquals(computed_qty, order_line.product_uom_qty * corr_bom_line.product_qty)

        # Processe enough componenents in the picking to make 2 kit_uom_1
        # Then create a backorder for the missing components
        qty_to_process = {
            component_uom_unit: 48,
            component_uom_dozen: 3,
            component_uom_kg: 0.006
        }
        self._process_quantities(move_lines, qty_to_process)
        backorder_wizard = self.env['stock.backorder.confirmation'].create(
            {'pick_ids': [(4, so.picking_ids[0].id)]})
        backorder_wizard.process()

        # Check that a backorder is created
        self.assertEquals(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEquals(backorder_1.backorder_id.id, picking_original.id)

        # Only 2 kits should be delivered
        self.assertEquals(order_line.qty_delivered, 2)

        # Adding missing components
        qty_to_process = {
            component_uom_unit: 192,
            component_uom_dozen: 7,
            component_uom_kg: 0.024
        }
        self._process_quantities(backorder_1.move_lines, qty_to_process)

        # Validating the last backorder now it's complete
        backorder_1.button_validate()
        order_line._compute_qty_delivered()
        # All kits should be delivered
        self.assertEquals(order_line.qty_delivered, 10)

    @mute_logger('odoo.tests.common.onchange')
    def test_07_kit_availability_mixed_uom(self):
        """
        Check that the 'Not enough inventory' warning message displays correct
        informations when a kit with multiple UoMs on its components is ordered
        """

        # Create some components
        component_uom_unit = self._create_product('Comp Unit', self.uom_unit)
        component_uom_dozen = self._create_product('Comp Dozen', self.uom_dozen)
        component_uom_kg = self._create_product('Comp Kg', self.uom_kg)
        component_uom_gm = self._create_product('Comp g', self.uom_gm)
        components = [component_uom_unit, component_uom_dozen, component_uom_kg, component_uom_gm]

        # Create a kit 'kit_uom_in_kit' :
        # -----------------------
        # kit_uom_in_kit --|- component_uom_gm  x3 Test-KG
        #                  |- kit_uom_1         x2 Test-Dozen --|- component_uom_unit    x2 Test-Dozen
        #                                                       |- component_uom_dozen   x1 Test-Dozen
        #                                                       |- component_uom_kg      x3 Test-G

        kit_uom_1 = self._create_product('Sub Kit 1', self.uom_unit)
        kit_uom_in_kit = self._create_product('Parent Kit', self.uom_unit)

        bom_kit_uom_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_uom_1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine = self.env['mrp.bom.line']
        BomLine.create({
            'product_id': component_uom_unit.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_dozen.id,
            'bom_id': bom_kit_uom_1.id})
        BomLine.create({
            'product_id': component_uom_dozen.id,
            'product_qty': 1.0,
            'product_uom_id': self.uom_dozen.id,
            'bom_id': bom_kit_uom_1.id})
        BomLine.create({
            'product_id': component_uom_kg.id,
            'product_qty': 3.0,
            'product_uom_id': self.uom_gm.id,
            'bom_id': bom_kit_uom_1.id})

        bom_kit_uom_in_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_uom_in_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'})

        BomLine.create({
            'product_id': component_uom_gm.id,
            'product_qty': 3.0,
            'product_uom_id': self.uom_kg.id,
            'bom_id': bom_kit_uom_in_kit.id})
        BomLine.create({
            'product_id': kit_uom_1.id,
            'product_qty': 2.0,
            'product_uom_id': self.uom_dozen.id,
            'bom_id': bom_kit_uom_in_kit.id})

        # Create a simple warehouse to receives some products
        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1'
        })

        # Set enough quantities to make 1 kit_uom_in_kit in WH1
        self.env['stock.quant']._update_available_quantity(component_uom_unit, warehouse_1.lot_stock_id, 576)
        self.env['stock.quant']._update_available_quantity(component_uom_dozen, warehouse_1.lot_stock_id, 24)
        self.env['stock.quant']._update_available_quantity(component_uom_kg, warehouse_1.lot_stock_id, 0.072)
        self.env['stock.quant']._update_available_quantity(component_uom_gm, warehouse_1.lot_stock_id, 3000)

        # Creation of a sale order for x5 kit_uom_in_kit
        qty_ordered = 5
        f = Form(self.env['sale.order'])
        f.partner_id = self.env.ref('base.res_partner_1')
        f.warehouse_id = warehouse_1
        with f.order_line.new() as line:
            line.product_id = kit_uom_in_kit
            line.product_uom_qty = qty_ordered

        so = f.save()
        order_line = so.order_line[0]

        # Check that not enough enough quantities are available in the warehouse set in the SO
        # but there are enough quantities in Warehouse 1 for 1 kit_parent
        kit_uom_in_kit.with_context(warehouse=warehouse_1.id)._compute_quantities()
        virtual_available_wh_order = kit_uom_in_kit.virtual_available
        self.assertEquals(virtual_available_wh_order, 1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)

        # We receive enough of each component in Warehouse 1 to make 3 kit_uom_in_kit.
        # Moves are created instead of only updating the quant quantities in order to trigger every compute fields.
        qty_to_process = {
            component_uom_unit: (1152, self.uom_unit),
            component_uom_dozen: (48, self.uom_dozen),
            component_uom_kg: (0.144, self.uom_kg),
            component_uom_gm: (6000, self.uom_gm)
        }
        self._create_move_quantities(qty_to_process, components, warehouse_1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)
        kit_uom_in_kit.with_context(warehouse=warehouse_1.id)._compute_quantities()
        virtual_available_wh_order = kit_uom_in_kit.virtual_available
        self.assertEquals(virtual_available_wh_order, 3)

        # We process enough quantities to have enough kit_uom_in_kit available for the sale order.
        self._create_move_quantities(qty_to_process, components, warehouse_1)

        # We check that enough quantities were processed to sell 5 kit_uom_in_kit
        kit_uom_in_kit.with_context(warehouse=warehouse_1.id)._compute_quantities()
        self.assertEquals(kit_uom_in_kit.virtual_available, 5)

    def test_10_sale_mrp_kits_routes(self):

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # kit_1 --|- component_shelf1   x3
        #         |- component_shelf2   x2

        kit_1 = self._create_product('Kit1', self.uom_unit)
        component_shelf1 = self._create_product('Comp Shelf1', self.uom_unit)
        component_shelf2 = self._create_product('Comp Shelf2', self.uom_unit)

        with Form(self.env['mrp.bom']) as bom:
            bom.product_tmpl_id = kit_1.product_tmpl_id
            bom.product_qty = 1
            bom.product_uom_id = self.uom_unit
            bom.type = 'phantom'
            with bom.bom_line_ids.new() as line:
                line.product_id = component_shelf1
                line.product_qty = 3
                line.product_uom_id = self.uom_unit
            with bom.bom_line_ids.new() as line:
                line.product_id = component_shelf2
                line.product_qty = 2
                line.product_uom_id = self.uom_unit

        # Creating 2 specific routes for each of the components of the kit
        route_shelf1 = self.env['stock.location.route'].create({
            'name': 'Shelf1 -> Customer',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Shelf1 -> Customer',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_in'),
                'location_src_id': self.ref('stock.stock_location_components'),
                'location_id': self.ref('stock.stock_location_customers'),
            })],
        })

        route_shelf2 = self.env['stock.location.route'].create({
            'name': 'Shelf2 -> Customer',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Shelf2 -> Customer',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_in'),
                'location_src_id': self.ref('stock.stock_location_14'),
                'location_id': self.ref('stock.stock_location_customers'),
            })],
        })

        component_shelf1.write({
            'route_ids': [(4, route_shelf1.id)]})
        component_shelf2.write({
            'route_ids': [(4, route_shelf2.id)]})

        # Set enough quantities to make 1 kit_uom_in_kit in WH1
        self.env['stock.quant']._update_available_quantity(component_shelf1, self.env.ref('stock.warehouse0').lot_stock_id, 15)
        self.env['stock.quant']._update_available_quantity(component_shelf2, self.env.ref('stock.warehouse0').lot_stock_id, 10)

        # Creating a sale order for 5 kits and confirming it
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.env.ref('base.res_partner_2')
        with order_form.order_line.new() as line:
            line.product_id = kit_1
            line.product_uom = self.uom_unit
            line.product_uom_qty = 5
        order = order_form.save()
        order.action_confirm()

        # Now we check that the routes of the components were applied, in order to make sure the routes set
        # on the kit itself are ignored
        self.assertEquals(len(order.picking_ids), 2)
        self.assertEquals(len(order.picking_ids[0].move_lines), 1)
        self.assertEquals(len(order.picking_ids[1].move_lines), 1)
        moves = order.picking_ids.mapped('move_lines')
        move_shelf1 = moves.filtered(lambda m: m.product_id == component_shelf1)
        move_shelf2 = moves.filtered(lambda m: m.product_id == component_shelf2)
        self.assertEquals(move_shelf1.location_id.id, self.ref('stock.stock_location_components'))
        self.assertEquals(move_shelf1.location_dest_id.id, self.ref('stock.stock_location_customers'))
        self.assertEquals(move_shelf2.location_id.id, self.ref('stock.stock_location_14'))
        self.assertEquals(move_shelf2.location_dest_id.id, self.ref('stock.stock_location_customers'))

    def test_11_sale_mrp_explode_kits_uom_quantities(self):

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # 2x Dozens kit_1 --|- component_unit   x6 Units
        #                   |- component_kg     x7 Kg

        kit_1 = self._create_product('Kit1', self.uom_unit)
        component_unit = self._create_product('Comp Unit', self.uom_unit)
        component_kg = self._create_product('Comp Kg', self.uom_kg)

        with Form(self.env['mrp.bom']) as bom:
            bom.product_tmpl_id = kit_1.product_tmpl_id
            bom.product_qty = 2
            bom.product_uom_id = self.uom_dozen
            bom.type = 'phantom'
            with bom.bom_line_ids.new() as line:
                line.product_id = component_unit
                line.product_qty = 6
                line.product_uom_id = self.uom_unit
            with bom.bom_line_ids.new() as line:
                line.product_id = component_kg
                line.product_qty = 7
                line.product_uom_id = self.uom_kg

        # Create a simple warehouse to receives some products
        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1'
        })
        # Set enough quantities to make 1 Test-Dozen kit_uom_in_kit
        self.env['stock.quant']._update_available_quantity(component_unit, warehouse_1.lot_stock_id, 12)
        self.env['stock.quant']._update_available_quantity(component_kg, warehouse_1.lot_stock_id, 14)

        # Creating a sale order for 3 Units of kit_1 and confirming it
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.env.ref('base.res_partner_2')
        order_form.warehouse_id = warehouse_1
        with order_form.order_line.new() as line:
            line.product_id = kit_1
            line.product_uom = self.uom_unit
            line.product_uom_qty = 2
        order = order_form.save()
        order.action_confirm()

        # Now we check that the routes of the components were applied, in order to make sure the routes set
        # on the kit itself are ignored
        self.assertEquals(len(order.picking_ids), 1)
        self.assertEquals(len(order.picking_ids[0].move_lines), 2)

        # Finally, we check the quantities for each component on the picking
        move_component_unit = order.picking_ids[0].move_lines.filtered(lambda m: m.product_id == component_unit)
        move_component_kg = order.picking_ids[0].move_lines - move_component_unit
        self.assertEquals(move_component_unit.product_uom_qty, 0.5)
        self.assertEquals(move_component_kg.product_uom_qty, 0.583)

    def test_product_type_service_1(self):
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Create finished product
        finished_product = self.env['product.product'].create({
            'name': 'Geyser',
            'type': 'product',
            'route_ids': [(4, route_mto), (4, route_manufacture)],
        })

        # Create service type product
        product_raw = self.env['product.product'].create({
            'name': 'raw Geyser',
            'type': 'service',
        })

        # Create bom for finish product
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': product_raw.id})]
        })

        # Create sale order
        sale_form = Form(self.env['sale.order'])
        sale_form.partner_id = self.env.ref('base.res_partner_1')
        with sale_form.order_line.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_uom_qty = 1.0
            line.product_uom = self.uom_unit
            line.price_unit = 10.0
        sale_order = sale_form.save()

        with self.assertRaises(UserError):
            sale_order.action_confirm()

        mo = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])

        self.assertTrue(mo, 'Manufacturing order created.')

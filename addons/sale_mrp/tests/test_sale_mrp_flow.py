# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import common, Form
from odoo.exceptions import UserError


class TestSaleMrpFlow(common.TransactionCase):

    def setUp(self):
        super(TestSaleMrpFlow, self).setUp()
        # Useful models
        self.StockMove = self.env['stock.move']
        self.UoM = self.env['uom.uom']
        self.MrpProduction = self.env['mrp.production']
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        self.ProductProduce = self.env['mrp.product.produce']
        self.ProductCategory = self.env['product.category']

        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('uom.product_uom_categ_kgm')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env.ref('stock.warehouse0')

    def test_00_sale_mrp_flow(self):
        """ Test sale to mrp flow with diffrent unit of measure."""
        def create_product(name, uom_id, routes=()):
            p = Form(self.env['product.product'])
            p.name = name
            p.type = 'product'
            p.uom_id = uom_id
            p.uom_po_id = uom_id
            p.route_ids.clear()
            for r in routes:
                p.route_ids.add(r)
            return p.save()

        self.uom_kg = self.env['uom.uom'].search([('category_id', '=', self.categ_kgm.id), ('uom_type', '=', 'reference')], limit=1)
        self.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001})
        self.uom_gm = self.UoM.create({
            'name': 'Test-G',
            'category_id': self.categ_kgm.id,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        self.uom_unit = self.env['uom.uom'].search([('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 1.0})
        self.uom_dozen = self.UoM.create({
            'name': 'Test-DozenA',
            'category_id': self.categ_unit.id,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Create product A, B, C, D.
        # --------------------------
        route_manufacture = self.warehouse.manufacture_pull_id.route_id
        route_mto = self.warehouse.mto_pull_id.route_id
        product_a = create_product('Product A', self.uom_unit, routes=[route_manufacture, route_mto])
        product_c = create_product('Product C', self.uom_kg)
        product_b = create_product('Product B', self.uom_dozen, routes=[route_manufacture, route_mto])
        product_d = create_product('Product D', self.uom_unit, routes=[route_manufacture, route_mto])

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
            'product_id': product_c.id,
            'filter': 'product'})

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
        self.assertEqual(mnf_product_d.availability, 'assigned', 'Availability should be assigned')
        self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # ------------------
        # produce product D.
        # ------------------

        produce_form = Form(self.ProductProduce.with_context({
            'active_id': mnf_product_d.id,
            'active_ids': [mnf_product_d.id],
        }))
        produce_form.product_qty = 20
        produce_d = produce_form.save()
        # produce_d.on_change_qty()
        produce_d.do_produce()
        mnf_product_d.post_inventory()

        # Check state of manufacturing order.
        self.assertEqual(mnf_product_d.state, 'progress', 'Manufacturing order should still be in progress state.')
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
            'product_id': product_c.id,
            'filter': 'product'})

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
        self.assertEqual(mnf_product_a.availability, 'assigned', 'Manufacturing order inventory state should be available.')
        moves = self.StockMove.search([('raw_material_production_id', '=', mnf_product_a.id), ('product_id', '=', product_c.id)])

        # Check product c move line state.
        for move in moves:
            self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # Produce product A.
        # ------------------
        produce_a = self.ProductProduce.with_context(
            # {'active_ids': [mnf_product_a.id], 'active_id': mnf_product_a.id}).create({'mode': 'consume_produce', 'product_qty': mnf_product_a.product_qty})
        # produce_a.on_change_qty()
            {'active_ids': [mnf_product_a.id], 'active_id': mnf_product_a.id}).create({})
        produce_a.do_produce()
        mnf_product_a.post_inventory()

        # Check state of manufacturing order product A.
        self.assertEqual(mnf_product_a.state, 'progress', 'Manufacturing order should still be in the progress state.')
        # Check product A avaialble quantity should be 120.
        self.assertEqual(product_a.qty_available, 120, 'Wrong quantity available of product A.')

    def test_01_sale_mrp_delivery_kit(self):
        """ Test delivered quantity on SO based on delivered quantity in pickings."""
        # intial so
        product = self.env.ref('mrp.product_product_table_kit')
        self.env['stock.quant']._update_available_quantity(product, self.stock_location, -product.qty_available)
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
            so.action_invoice_create()
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
        pick_2 = so.picking_ids[0]
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
        account_type = self.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = self.account_receiv
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = self.account_receiv
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = self.account_receiv
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

        price_list_EUR = self.env.ref('product.list0').copy({'currency_id': self.env.ref('base.EUR').id})

        # Create a SO for a specific partner for three units of the finished product
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.finished_product.name, 'product_id': self.finished_product.id, 'product_uom_qty': 3, 'product_uom': self.finished_product.uom_id.id, 'price_unit': self.finished_product.list_price})],
            'pricelist_id': price_list_EUR.id,
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
        self.so.action_invoice_create()
        self.invoice = self.so.invoice_ids
        # Changed the invoiced quantity of the finished product to 2
        self.invoice.invoice_line_ids.write({'quantity': 2.0})
        self.invoice.action_invoice_open()
        aml = self.invoice.move_id.line_ids
        aml_expense = aml.filtered(lambda l: l.account_id.id == account_expense.id)
        aml_output = aml.filtered(lambda l: l.account_id.id == account_output.id)
        # Check that the cost of Good Sold entries are equal to 2* (2 * 20 + 1 * 10) = 100
        self.assertEqual(aml_expense.debit, 100, "Cost of Good Sold entry missing or mismatching")
        self.assertEqual(aml_output.credit, 100, "Cost of Good Sold entry missing or mismatching")

    def test_03_sale_mrp_anglo_saxon(self):
        """Test the price unit of a kit"""
        # This test will check that the correct journal entries are created when a consumable product in real time valuation
        # and in fifo cost method is sold in a company using anglo-saxon.
        # For this test, let's consider a product category called Test category in real-time valuation and real price costing method
        # Let's  also consider a finished product with a bom with two components: component1(cost = 20) and component2(cost = 10)
        # These products are in the Test category
        # The bom consists of 2 component1 and 1 component2
        # The invoice policy of the finished product is based on delivered quantities
        self.uom_unit = self.uom_unit = self.env['uom.uom'].search([('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.company = self.env.ref('base.main_company')
        self.company.anglo_saxon_accounting = True
        self.partner = self.env.ref('base.res_partner_1')
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category','property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_type = self.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = self.account_receiv
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = self.account_receiv
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = self.account_receiv
        self.category.property_stock_journal = self.env['account.journal'].create({'name': 'Stock journal', 'type': 'sale', 'code': 'STK00'})

        Product = self.env['product.product']
        self.finished_product = Product.create({
                'name': 'Finished product',
                'type': 'consu',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'delivery',
                'categ_id': self.category.id,
                'taxes_id': [(6, 0, [])],
                'list_price': 60})
        self.component1 = Product.create({
                'name': 'Component 1',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'delivery',
                'categ_id': self.category.id,
                'taxes_id': [(6, 0, [])],
                'standard_price': 20})
        self.component2 = Product.create({
                'name': 'Component 2',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'invoice_policy': 'delivery',
                'categ_id': self.category.id,
                'taxes_id': [(6, 0, [])],
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

        price_list = self.env.ref('product.list0').copy({'currency_id': self.company.currency_id.id})

        # Create a SO for a specific partner for three units of the finished product
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.finished_product.name, 'product_id': self.finished_product.id, 'product_uom_qty': 3, 'product_uom': self.finished_product.uom_id.id, 'price_unit': 60.0})],
            'pricelist_id': price_list.id,
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
        self.so.action_invoice_create()
        self.invoice = self.so.invoice_ids
        self.invoice.action_invoice_open()
        aml = self.invoice.move_id.line_ids
        aml_receivable = aml.filtered(lambda l: l.account_id.id == self.account_receiv.id and l.debit > 0.0)
        aml_income = aml.filtered(lambda l: l.account_id.id == self.account_receiv.id and l.credit > 0.0)
        aml_expense = aml.filtered(lambda l: l.account_id.id == account_expense.id)
        aml_output = aml.filtered(lambda l: l.account_id.id == account_output.id)
        self.assertEqual(aml_receivable.debit, 180, "Cost of Good Sold entry missing or mismatching")
        self.assertEqual(aml_income.credit, 180, "Cost of Good Sold entry missing or mismatching")
        # Check that the cost of Good Sold entries are equal to 3* (2 * 20 + 1 * 10) = 150
        self.assertEqual(aml_expense.debit, 150, "Cost of Good Sold entry missing or mismatching")
        self.assertEqual(aml_output.credit, 150, "Cost of Good Sold entry missing or mismatching")

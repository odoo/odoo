# -*- coding: utf-8 -*-

from openerp.tests import common
from datetime import datetime


class TestSaleMrpFlow(common.TransactionCase):

    def setUp(self):
        super(TestSaleMrpFlow, self).setUp()
        # Usefull models
        self.SaleOrderLine = self.env['sale.order.line']
        self.SaleOrder = self.env['sale.order']
        self.MrpBom = self.env['mrp.bom']
        self.StockMove = self.env['stock.move']
        self.MrpBomLine = self.env['mrp.bom.line']
        self.ProductUom = self.env['product.uom']
        self.MrpProduction = self.env['mrp.production']
        self.Product = self.env['product.product']
        self.ProcurementOrder = self.env['procurement.order']
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        self.ProductProduce = self.env['mrp.product.produce']

        self.partner_agrolite = self.env.ref('base.res_partner_2')
        self.categ_unit = self.env.ref('product.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('product.product_uom_categ_kgm')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env.ref('stock.warehouse0')

    def test_00_sale_mrp_flow(self):
        """Test sale to mrp flow with diffrent unit of measure."""
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id

        self.uom_kg = self.ProductUom.create({
            'name': 'Test-KG',
            'category_id': self.categ_kgm.id,
            'factor_inv': 1,
            'factor': 1,
            'uom_type': 'reference',
            'rounding': 0.000001})
        self.uom_gm = self.ProductUom.create({
            'name': 'Test-G',
            'category_id': self.categ_kgm.id,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})

        self.uom_unit = self.ProductUom.create({
            'name': 'Test-Unit',
            'category_id': self.categ_unit.id,
            'factor': 1,
            'uom_type': 'reference',
            'rounding': 1.0})
        self.uom_dozen = self.ProductUom.create({
            'name': 'Test-DozenA',
            'category_id': self.categ_unit.id,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})

        # Create product C.
        # ------------------
        product_c = self.Product.create({
            'type': 'product',
            'name': 'Product C',
            'uom_id': self.uom_kg.id,
            'uom_po_id': self.uom_kg.id})

        # Create product B and its bill of materials.
        # ---------------------------------------------
        product_b = self.Product.create({
            'name': 'Product B',
            'type': 'product',
            'uom_id': self.uom_dozen.id,
            'uom_po_id': self.uom_dozen.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Bill of materials for Product B.
        bom_b = self.MrpBom.create({
            'name': product_b.name,
            'product_tmpl_id': product_b.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom': self.uom_unit.id,
            'product_efficiency': 1.0,
            'type': 'phantom'})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 0.400,
            'bom_id': bom_b.id,
            'product_uom': self.uom_kg.id})

        # Create product D and its bill of materials.
        # -----------------------------------------------
        product_d = self.Product.create({
            'name': 'Product D',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})
        # Bill of materials for Product D.
        bom_d = self.MrpBom.create({
            'name': product_d.name,
            'product_tmpl_id': product_d.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom': self.uom_unit.id,
            'product_efficiency': 1.0,
            'type': 'normal'})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 1,
            'bom_id': bom_d.id,
            'product_uom': self.uom_kg.id})

        # Create product A and its bill of materials.
        # -------------------------------------------
        product_a = self.Product.create({
            'name': 'Product A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Bill of materials for Product A.
        bom_a = self.MrpBom.create({
            'name': product_d.name,
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'product_qty': 2,
            'product_uom': self.uom_dozen.id,
            'product_efficiency': 1.0,
            'type': 'normal'})

        self.MrpBomLine.create({
            'product_id': product_b.id,
            'product_qty': 3,
            'type': 'phantom',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})

        self.MrpBomLine.create({
            'product_id': product_c.id,
            'product_qty': 300.5,
            'type': 'normal',
            'bom_id': bom_a.id,
            'product_uom': self.uom_gm.id})

        self.MrpBomLine.create({
            'product_id': product_d.id,
            'product_qty': 4,
            'type': 'phantom',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})

        self.MrpBomLine.create({
            'product_id': product_d.id,
            'product_qty': 4,
            'type': 'normal',
            'bom_id': bom_a.id,
            'product_uom': self.uom_unit.id})
        # ----------------------------------------
        # Create Sale order of 10 Dozen product A.
        # ----------------------------------------
        order = self.SaleOrder.create({
            'partner_id': self.partner_agrolite.id,
            'date_order': datetime.today(),
        })
        self.SaleOrderLine.create({
            'order_id': order.id,
            'product_id': product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.uom_dozen.id
        })
        assert order, "Sale order not created."
        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_button_confirm()

        # Run procurement.
        # ---------------
        procurements = self.ProcurementOrder.search([('origin', 'like', order.name)])
        procurements.run()

        # ----------------------------------------------------
        # Check manufacturing order for product A.
        # ----------------------------------------------------

        mnf_product_a = self.MrpProduction.search([('origin', 'like', order.name), ('product_id', '=', product_a.id)])
        self.assertEqual(len(mnf_product_a), 1, 'Manufacturing order not created.')
        # Check quantity, unit of measure and state of manufacturing order.
        self.assertEqual(mnf_product_a.product_qty, 10, 'Wrong product quantity in manufacturing order.')
        self.assertEqual(mnf_product_a.product_uom.id, self.uom_dozen.id, 'Wrong unit of measure in manufacturing order.')
        self.assertEqual(mnf_product_a.state, 'confirmed', 'Manufacturing order should be confirmed.')

        # Check move lines of manufacturing order for product A.
        #  --------------------------------------------------

        # Check move lines for product c with uom kg.
        moves = self.StockMove.search([
            ('origin', 'like', mnf_product_a.name),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_kg.id)])
        self.assertEqual(len(moves), 2, 'Production move lines are not generated proper.')
        list_qty = [move.product_uom_qty for move in moves]
        # Check quantity of product c.
        self.assertEqual(set(list_qty), set([6.0, 20.0]), 'Wrong product quantity in move lines of manufacturing order.')
        # Check move lines for product c with uom gm.
        move = self.StockMove.search([
            ('origin', 'like', mnf_product_a.name),
            ('product_id', '=', product_c.id),
            ('product_uom', '=', self.uom_gm.id)])
        self.assertEqual(len(move), 1, 'Production move lines are not generated proper.')
        # Check quantity of product c.
        self.assertEqual(move.product_uom_qty, 1502.5, 'Wrong quantity in move line of manufacturing order.')
        # Check state in move lines for product c.
        moves = self.StockMove.search([
            ('origin', 'like', mnf_product_a.name),
            ('product_id', '=', product_c.id)])
        self.assertEqual(len(moves), 3, 'Production move lines are not generated proper.')
        for move in moves:
            self.assertEqual(move.state, 'confirmed', 'Wrong state in move line of manufacturing order.')
        move = self.StockMove.search([
            ('origin', 'like', mnf_product_a.name),
            ('product_id', '=', product_d.id)])
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')
        self.assertEqual(move.state, 'waiting', 'Wrong state in move line of manufacturing order.')
        self.assertEqual(move.product_uom_qty, 20, 'Wrong quantity in move line of manufacturing order.')

        # -----------------------------------------------------------------------------------------
        # Manufacturing order for product D.
        # -----------------------------------------------------------------------------------------

        # Run procurement for product D.
        procurement = self.ProcurementOrder.search([('origin', 'like', mnf_product_a.name)])
        self.assertEqual(len(procurement), 1, 'Procurement order not generated proper.')
        procurement.run()
        # Check manufacturing order for product D created or not.
        mnf_product_d = self.MrpProduction.search([('origin', 'like', mnf_product_a.name), ('product_id', '=', product_d.id)])
        # Check manufacturing order move states and quantity of product D.
        move = self.StockMove.search([('origin', 'like', mnf_product_d.name), ('product_id', '=', product_c.id)])
        self.assertEqual(mnf_product_d.state, 'confirmed', 'Manufacturing order should be confirmed.')
        self.assertEqual(len(move), 1, 'Production lines are not generated proper.')
        self.assertEqual(move.product_uom_qty, 20, 'Wrong quantity in move line of manufacturing order.')
        self.assertEqual(move.product_uom.id, self.uom_kg.id, 'Wrong unit of measure in move line of manufacturing order.')
        self.assertEqual(move.state, 'confirmed', 'Wrong state in move line of manufacturing order.')

        # -------------------------------
        # Create Inventory for product c.
        # -------------------------------

        inventory = self.Inventory.create({
            'name': 'Inventory Product KG',
            'product_id': product_c.id,
            'filter': 'product'})

        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 20,
            'location_id': self.stock_location.id})
        inventory.action_done()

        # --------------------------------------------------
        # Assign product c to manufacturing order of product D.
        # --------------------------------------------------

        mnf_product_d.action_assign()
        self.assertEqual(mnf_product_d.state, 'ready', 'Manufacturing order should be ready.')
        move = self.StockMove.search([('origin', 'like', mnf_product_d.name), ('product_id', '=', product_c.id)])
        self.assertEqual(move.state, 'assigned', 'Wrong move line state of manufacturing order.')
        # produce product D.
        # ------------------

        produce_d = self.ProductProduce.with_context({'active_ids': [mnf_product_d.id], 'active_id': mnf_product_d.id}).create({
            'mode': 'consume_produce',
            'product_qty': 20})
        lines = produce_d.on_change_qty(mnf_product_d.product_qty, [])
        produce_d.write(lines['value'])
        produce_d.do_produce()
        # Check state of manufacturing order
        self.assertEqual(mnf_product_d.state, 'done', 'Manufacturing order should be done.')
        # Check available quantity of product D.
        self.assertEqual(product_d.qty_available, 20, 'Wrong quantity available of product D.')

        # --------------------------------------------------
        # Assign product to manufacturing order of product A.
        # --------------------------------------------------

        mnf_product_a.action_assign()
        self.assertEqual(mnf_product_a.state, 'confirmed', 'Manufacturing order should be confirmed.')
        move = self.StockMove.search([('origin', 'like', mnf_product_a.name), ('product_id', '=', product_d.id)])
        self.assertEqual(move.state, 'assigned', 'Wrong move line state of manufacturing order.')

        # Create Inventry for product C
        inventory = self.Inventory.create({
            'name': 'Inventory Product C KG',
            'product_id': product_c.id,
            'filter': 'product'})

        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_c.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 27.5025,
            'location_id': self.stock_location.id})
        inventory.action_done()

        # Assign product to manufacturing order of product A.
        # ---------------------------------------------------
        mnf_product_a.action_assign()
        self.assertEqual(mnf_product_a.state, 'ready', 'Manufacturing order should be ready.')
        moves = self.StockMove.search([('origin', 'like', mnf_product_a.name), ('product_id', '=', product_c.id)])
        # Check product c move line state.
        for move in moves:
            self.assertEqual(move.state, 'assigned', 'Wrong move line state of manufacturing order.')

        # Produce product A.
        # ------------------

        produce_a = self.ProductProduce.with_context({
            'active_ids': [mnf_product_a.id], 'active_id': mnf_product_a.id}).create({
                'mode': 'consume_produce'})
        lines = produce_a.on_change_qty(mnf_product_a.product_qty, [])
        produce_a.write(lines['value'])
        produce_a.do_produce()
        # Check state of manufacturing order
        self.assertEqual(mnf_product_a.state, 'done', 'Manufacturing order should be done.')
        # Check available quantity of product A.
        self.assertEqual(product_a.qty_available, 120, 'Wrong quantity available of product.')

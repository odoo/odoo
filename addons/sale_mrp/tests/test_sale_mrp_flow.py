# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import common
from odoo.exceptions import UserError


class TestSaleMrpFlow(common.TransactionCase):

    def setUp(self):
        super(TestSaleMrpFlow, self).setUp()
        # Useful models
        self.SaleOrderLine = self.env['sale.order.line']
        self.SaleOrder = self.env['sale.order']
        self.MrpBom = self.env['mrp.bom']
        self.StockMove = self.env['stock.move']
        self.MrpBomLine = self.env['mrp.bom.line']
        self.ProductUom = self.env['product.uom']
        self.MrpProduction = self.env['mrp.production']
        self.Product = self.env['product.product']
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        self.ProductProduce = self.env['mrp.product.produce']

        self.partner_agrolite = self.env.ref('base.res_partner_2')
        self.categ_unit = self.env.ref('product.product_uom_categ_unit')
        self.categ_kgm = self.env.ref('product.product_uom_categ_kgm')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.warehouse = self.env.ref('stock.warehouse0')

    def test_00_sale_mrp_flow(self):
        """ Test sale to mrp flow with diffrent unit of measure."""
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id

        def create_product(name, uom_id, route_ids=[]):
            return self.Product.create({
                'name': name,
                'type': 'product',
                'uom_id': uom_id,
                'uom_po_id': uom_id,
                'route_ids': route_ids})

        def create_bom_lines(bom_id, product_id, qty, uom_id, procure_method): #TODO: remove procure_method
            self.MrpBomLine.create({
                'product_id': product_id,
                'product_qty': qty,
                'bom_id': bom_id,
                'product_uom_id': uom_id})

        def create_bom(product_tmpl_id, qty, uom_id, type):
            return self.MrpBom.create({
                'product_tmpl_id': product_tmpl_id,
                'product_qty': qty,
                'type': type,
                'product_uom_id': uom_id})

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

        # Create product A, B, C, D.
        # --------------------------
        product_a = create_product('Product A', self.uom_unit.id, route_ids=[(6, 0, [route_manufacture, route_mto])])
        product_c = create_product('Product C', self.uom_kg.id, route_ids=[])
        product_b = create_product('Product B', self.uom_dozen.id, route_ids=[(6, 0, [route_manufacture, route_mto])])
        product_d = create_product('Product D', self.uom_unit.id, route_ids=[(6, 0, [route_manufacture, route_mto])])

        # ------------------------------------------------------------------------------------------
        # Bill of materials for product A, B, D.
        # ------------------------------------------------------------------------------------------

        # Bill of materials for Product A.
        bom_a = create_bom(product_a.product_tmpl_id.id, 2, self.uom_dozen.id, 'normal')
        create_bom_lines(bom_a.id, product_b.id, 3, self.uom_unit.id, 'make_to_order')
        create_bom_lines(bom_a.id, product_c.id, 300.5, self.uom_gm.id, 'make_to_stock')
        create_bom_lines(bom_a.id, product_d.id, 4, self.uom_unit.id, 'make_to_order')

        # Bill of materials for Product B.
        bom_b = create_bom(product_b.product_tmpl_id.id, 1, self.uom_unit.id, 'phantom')
        create_bom_lines(bom_b.id, product_c.id, 0.400, self.uom_kg.id, 'make_to_stock')

        # Bill of materials for Product D.
        bom_d = create_bom(product_d.product_tmpl_id.id, 1, self.uom_unit.id, 'normal')
        create_bom_lines(bom_d.id, product_c.id, 1, self.uom_kg.id, 'make_to_stock')

        # ----------------------------------------
        # Create sales order of 10 Dozen product A.
        # ----------------------------------------

        order = self.SaleOrder.create({
            'partner_id': self.partner_agrolite.id,
            'partner_invoice_id': self.partner_agrolite.id,
            'partner_shipping_id': self.partner_agrolite.id,
            'date_order': datetime.today(),
            'pricelist_id': self.env.ref('product.list0').id,
        })
        self.SaleOrderLine.create({
            'name': product_a.name,
            'order_id': order.id,
            'product_id': product_a.id,
            'product_uom_qty': 10,
            'product_uom': self.uom_dozen.id
        })
        self.assertTrue(order, "Sales order not created.")
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
        self.assertEqual(mnf_product_a.product_uom_id.id, self.uom_unit.id, 'Wrong unit of measure in manufacturing order.')
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
        mnf_product_d = self.MrpProduction.search([('product_id', '=', product_d.id), ('move_dest_ids.group_id', '=', order.procurement_group_id.id)], order='id desc', limit=1)
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
        inventory.action_done()

        # --------------------------------------------------
        # Assign product c to manufacturing order of product D.
        # --------------------------------------------------

        mnf_product_d.action_assign()
        self.assertEqual(mnf_product_d.availability, 'assigned', 'Availability should be assigned')
        self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # ------------------
        # produce product D.
        # ------------------

        produce_d = self.ProductProduce.with_context({'active_ids': [mnf_product_d.id], 'active_id': mnf_product_d.id}).create({
            'product_qty': 20})
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
        inventory.action_done()

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
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('mrp.product_product_build_kit')
        self.product.invoice_policy = 'delivery'
        # Remove the MTO route as purchase is not installed and since the procurement removal the exception is directly raised
        self.product.write({'route_ids': [(6, 0, [self.warehouse.manufacture_pull_id.route_id.id])]})
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.product.name, 'product_id': self.product.id, 'product_uom_qty': 5, 'product_uom': self.product.uom_id.id, 'price_unit': self.product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        self.so = self.SaleOrder.create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale MRP: no picking created for "invoice on delivery" stockable products')

        # invoice in on delivery, nothing should be invoiced
        with self.assertRaises(UserError):
            self.so.action_invoice_create()
        self.assertEqual(self.so.invoice_status, 'no', 'Sale MRP: so invoice_status should be "nothing to invoice" after invoicing')

        # deliver partially (1 of each instead of 5), check the so's invoice_status and delivered quantities
        pick = self.so.picking_ids
        pick.force_assign()
        pick.move_lines.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        self.assertEqual(self.so.invoice_status, 'no', 'Sale MRP: so invoice_status should be "no" after partial delivery of a kit')
        del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
        self.assertEqual(del_qty, 0.0, 'Sale MRP: delivered quantity should be zero after partial delivery of a kit')
        # deliver remaining products, check the so's invoice_status and delivered quantities
        self.assertEqual(len(self.so.picking_ids), 2, 'Sale MRP: number of pickings should be 2')
        pick_2 = self.so.picking_ids[0]
        pick_2.force_assign()
        pick_2.move_lines.write({'quantity_done': 4})
        pick_2.button_validate()

        del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
        self.assertEqual(del_qty, 5.0, 'Sale MRP: delivered quantity should be 5.0 after complete delivery of a kit')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale MRP: so invoice_status should be "to invoice" after complete delivery of a kit')

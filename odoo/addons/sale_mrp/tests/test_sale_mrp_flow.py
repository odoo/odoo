# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import common, Form
from odoo.exceptions import UserError
from odoo.tools import mute_logger, float_compare
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


# these tests create accounting entries, and therefore need a chart of accounts
class TestSaleMrpFlowCommon(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Required for `uom_id` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')
        cls.env.ref('stock.route_warehouse0_mto').active = True

        # Useful models
        cls.StockMove = cls.env['stock.move']
        cls.UoM = cls.env['uom.uom']
        cls.MrpProduction = cls.env['mrp.production']
        cls.Quant = cls.env['stock.quant']
        cls.ProductCategory = cls.env['product.category']

        cls.categ_unit = cls.env.ref('uom.product_uom_categ_unit')
        cls.categ_kgm = cls.env.ref('uom.product_uom_categ_kgm')

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
        cls.uom_ten = cls.UoM.create({
            'name': 'Test-Ten',
            'category_id': cls.categ_unit.id,
            'factor_inv': 10,
            'uom_type': 'bigger',
            'rounding': 0.001})
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
        p.detailed_type = 'product'
        p.uom_id = uom_id
        p.uom_po_id = uom_id
        p.route_ids.clear()
        for r in routes:
            p.route_ids.add(r)
        return p.save()

    def _create_product(self, name, uom_id, routes=()):
        p = Form(self.env['product.product'])
        p.name = name
        p.detailed_type = 'product'
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
            move.write({
                'quantity': quantities_to_process[move.product_id],
                'picked': True
            })

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
            # <field name="name" invisible="1"/>
            f.location_id = self.env.ref('stock.stock_location_suppliers')
            f.location_dest_id = warehouse.lot_stock_id
            f.product_id = comp
            f.product_uom = qty_to_process[comp][1]
            f.product_uom_qty = qty_to_process[comp][0]
            move = f.save()
            move._action_confirm()
            move._action_assign()
            move_line = move.move_line_ids[0]
            move_line.quantity = qty_to_process[comp][0]
            move._action_done()


@common.tagged('post_install', '-at_install')
class TestSaleMrpFlow(TestSaleMrpFlowCommon):
    def test_00_sale_mrp_flow(self):
        """ Test sale to mrp flow with diffrent unit of measure."""


        # Create product A, B, C, D.
        # --------------------------
        route_manufacture = self.company_data['default_warehouse'].manufacture_pull_id.route_id
        route_mto = self.company_data['default_warehouse'].mto_pull_id.route_id
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
                line.product_qty = 300.0
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
        order_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        with order_form.order_line.new() as line:
            line.product_id = product_a
            line.product_uom = self.uom_dozen
            line.product_uom_qty = 10
        order = order_form.save()
        order.action_confirm()

        # Verify buttons are working as expected
        self.assertEqual(order.mrp_production_count, 1, "User should see the closest manufacture order in the smart button")

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
        #        Product C  1500.0 gm.
        #                [
        #                  For 2 Dozen product A will consume 300.0 gm product C
        #                  then for 10 Dozen product A will consume 1500.0 gm product C.
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
        self.assertEqual(mnf_product_a.product_qty, 10, 'Wrong product quantity in manufacturing order.')
        self.assertEqual(mnf_product_a.product_uom_id, self.uom_dozen, 'Wrong unit of measure in manufacturing order.')
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
        # Check quantity should be with 1500.0 ( 2 Dozen product A consume 300.0 gm then 10 Dozen (300.0 * (10/2)).
        self.assertEqual(move.product_uom_qty, 1500.0, "Wrong product quantity in 'To consume line' of manufacturing order.")
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

        self.Quant.with_context(inventory_mode=True).create({
            'product_id': product_c.id, # uom = uom_kg
            'inventory_quantity': 20,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        }).action_apply_inventory()

        # --------------------------------------------------
        # Assign product c to manufacturing order of product D.
        # --------------------------------------------------

        mnf_product_d.action_assign()
        self.assertEqual(mnf_product_d.reservation_state, 'assigned', 'Availability should be assigned')
        self.assertEqual(move.state, 'assigned', "Wrong state in 'To consume line' of manufacturing order.")

        # ------------------
        # produce product D.
        # ------------------

        mo_form = Form(mnf_product_d)
        mo_form.qty_producing = 20
        mnf_product_d = mo_form.save()
        mnf_product_d._post_inventory()

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
        # Need product C ( 20 kg + 6 kg + 1500.0 gm = 27.500 kg)
        # -------------------------------------------------------

        self.Quant.with_context(inventory_mode=True).create({
            'product_id': product_c.id, # uom = uom_kg
            'inventory_quantity': 27.51, # round up due to kg.rounding = 0.01
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        }).action_apply_inventory()

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

        mo_form = Form(mnf_product_a)
        mo_form.qty_producing = mo_form.product_qty
        mnf_product_a = mo_form.save()
        mnf_product_a._post_inventory()
        # Check state of manufacturing order product A.
        self.assertEqual(mnf_product_a.state, 'done', 'Manufacturing order should still be in the progress state.')
        # Check product A avaialble quantity should be 120.
        self.assertEqual(product_a.qty_available, 120, 'Wrong quantity available of product A.')

    def test_01_sale_mrp_delivery_kit(self):
        """ Test delivered quantity on SO based on delivered quantity in pickings."""
        # intial so
        product = self.env['product.product'].create({
            'name': 'Table Kit',
            'type': 'consu',
            'invoice_policy': 'delivery',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # Remove the MTO route as purchase is not installed and since the procurement removal the exception is directly raised
        product.write({'route_ids': [(6, 0, [self.company_data['default_warehouse'].manufacture_pull_id.route_id.id])]})

        product_wood_panel = self.env['product.product'].create({
            'name': 'Wood Panel',
            'type': 'product',
        })
        product_desk_bolt = self.env['product.product'].create({
            'name': 'Bolt',
            'type': 'product',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'sequence': 2,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': product_wood_panel.id,
                    'product_qty': 1,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                }), (0, 0, {
                    'product_id': product_desk_bolt.id,
                    'product_qty': 4,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                })
            ]
        })

        partner = self.env['res.partner'].create({'name': 'My Test Partner'})
        # if `delivery` module is installed, a default property is set for the carrier to use
        # However this will lead to an extra line on the SO (the delivery line), which will force
        # the SO to have a different flow (and `invoice_state` value)
        if 'property_delivery_carrier_id' in partner:
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
        pick.move_ids.write({'quantity': 1, 'picked': True})
        wiz_act = pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()
        self.assertEqual(so.invoice_status, 'no', 'Sale MRP: so invoice_status should be "no" after partial delivery of a kit')
        del_qty = sum(sol.qty_delivered for sol in so.order_line)
        self.assertEqual(del_qty, 0.0, 'Sale MRP: delivered quantity should be zero after partial delivery of a kit')
        # deliver remaining products, check the so's invoice_status and delivered quantities
        self.assertEqual(len(so.picking_ids), 2, 'Sale MRP: number of pickings should be 2')
        pick_2 = so.picking_ids.filtered('backorder_id')
        for move in pick_2.move_ids:
            if move.product_id.id == product_desk_bolt.id:
                move.write({'quantity': 19, 'picked': True})
            else:
                move.write({'quantity': 4, 'picked': True})
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
        self.company = self.company_data['company']
        self.company.anglo_saxon_accounting = True
        self.partner = self.env['res.partner'].create({'name': 'My Test Partner'})
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category','property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00', 'account_type': 'asset_receivable', 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00', 'account_type': 'liability_current', 'reconcile': True})
        account_income = self.env['account.account'].create({'name': 'Income', 'code': 'INC00', 'account_type': 'asset_current', 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00', 'account_type': 'liability_current', 'reconcile': True})
        account_valuation = self.env['account.account'].create({'name': 'Valuation', 'code': 'STV00', 'account_type': 'asset_receivable', 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = account_income
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = account_income
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

        # Create quants with sudo to avoid:
        # "You are not allowed to create 'Quants' (stock.quant) records. No group currently allows this operation."
        self.env['stock.quant'].sudo().create({
            'product_id': self.component1.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'quantity': 6.0,
        })
        self.env['stock.quant'].sudo().create({
            'product_id': self.component2.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
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
            'company_id': self.company.id,
        }
        self.so = self.env['sale.order'].create(so_vals)
        # Validate the SO
        self.so.action_confirm()
        # Deliver the three finished products
        pick = self.so.picking_ids
        # To check the products on the picking
        self.assertEqual(pick.move_ids.mapped('product_id'), self.component1 | self.component2)
        pick.button_validate()
        # Create the invoice
        self.so._create_invoices()
        self.invoice = self.so.invoice_ids
        # Changed the invoiced quantity of the finished product to 2
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        self.invoice = move_form.save()
        self.invoice.action_post()
        aml = self.invoice.line_ids
        aml_expense = aml.filtered(lambda l: l.display_type == 'cogs' and l.debit > 0)
        aml_output = aml.filtered(lambda l: l.display_type == 'cogs' and l.credit > 0)
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
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 20)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_c, stock_location, 30)

        # Creation of a sale order for x10 kit_1
        partner = self.env['res.partner'].create({'name': 'My Test Partner'})
        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = self.kit_1
            line.product_uom_qty = 10.0

        # Confirming the SO to trigger the picking creation
        so = f.save()
        so.action_confirm()

        # Check picking creation
        self.assertEqual(len(so.picking_ids), 1)
        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids

        # Check if the correct amount of stock.moves are created
        self.assertEqual(len(move_ids), 3)

        # Check if BoM is created and is for a 'Kit'
        bom_from_k1 = self.env['mrp.bom']._bom_find(self.kit_1)[self.kit_1]
        self.assertEqual(self.bom_kit_1.id, bom_from_k1.id)
        self.assertEqual(bom_from_k1.type, 'phantom')

        # Check there's only 1 order line on the SO and it's for x10 'kit_1'
        order_lines = so.order_line
        self.assertEqual(len(order_lines), 1)
        order_line = order_lines[0]
        self.assertEqual(order_line.product_id.id, self.kit_1.id)
        self.assertEqual(order_line.product_uom_qty, 10.0)

        # Check if correct qty is ordered for each component of the kit
        expected_quantities = {
            self.component_a: 20,
            self.component_b: 10,
            self.component_c: 30,
        }
        self._assert_quantities(move_ids, expected_quantities)

        # Process only x1 of the first component then create a backorder for the missing components
        picking_original.move_ids.sorted()[0].write({'quantity': 1, 'picked': True})

        wiz_act = so.picking_ids[0].button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # Check that the backorder was created, no kit should be delivered at this point
        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)
        self.assertEqual(order_line.qty_delivered, 0)

        # Process only x6 each componenent in the picking
        # Then create a backorder for the missing components
        backorder_1.move_ids.write({'quantity': 6, 'picked': True})
        wiz_act = backorder_1.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # Check that a backorder is created
        self.assertEqual(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
        self.assertEqual(backorder_2.backorder_id.id, backorder_1.id)

        # With x6 unit of each components, we can only make 2 kits.
        # So only 2 kits should be delivered
        self.assertEqual(order_line.qty_delivered, 2)

        # Process x3 more unit of each components :
        # - Now only 3 kits should be delivered
        # - A backorder will be created, the SO should have 3 picking_ids linked to it.
        backorder_2.move_ids.write({'quantity': 3, 'picked': True})

        wiz_act = backorder_2.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        self.assertEqual(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - picking_original - backorder_2 - backorder_1
        self.assertEqual(backorder_3.backorder_id.id, backorder_2.id)
        self.assertEqual(order_line.qty_delivered, 3)

        # Adding missing components
        qty_to_process = {
            self.component_a: 10,
            self.component_b: 1,
            self.component_c: 21,
        }
        self._process_quantities(backorder_3.move_ids, qty_to_process)

        # Validating the last backorder now it's complete
        backorder_3.button_validate()
        order_line._compute_qty_delivered()

        # All kits should be delivered
        self.assertEqual(order_line.qty_delivered, 10)

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
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 56)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 28)
        self.env['stock.quant']._update_available_quantity(self.component_c, stock_location, 84)
        self.env['stock.quant']._update_available_quantity(self.component_d, stock_location, 14)
        self.env['stock.quant']._update_available_quantity(self.component_e, stock_location, 7)
        self.env['stock.quant']._update_available_quantity(self.component_f, stock_location, 14)
        self.env['stock.quant']._update_available_quantity(self.component_g, stock_location, 28)

        # Creation of a sale order for x7 kit_parent
        partner = self.env['res.partner'].create({'name': 'My Test Partner'})
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
        self.assertEqual(len(so.picking_ids), 1)
        order_line = so.order_line[0]
        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids
        products = move_ids.product_id
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

        self.assertEqual(len(move_ids), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_ids, expected_quantities)

        # Process only 7 units of each component
        qty_to_process = 7
        move_ids.write({'quantity': qty_to_process, 'picked': True})

        # Create a backorder for the missing componenents
        wiz_act = picking_original.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # Check that a backorded is created
        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        # Even if some components are delivered completely,
        # no KitParent should be delivered
        self.assertEqual(order_line.qty_delivered, 0)

        # Process just enough components to make 1 kit_parent
        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_ids, qty_to_process)

        # Create a backorder for the missing componenents
        wiz_act = backorder_1.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # Only 1 kit_parent should be delivered at this point
        self.assertEqual(order_line.qty_delivered, 1)

        # Check that the second backorder is created
        self.assertEqual(len(so.picking_ids), 3)
        backorder_2 = so.picking_ids - picking_original - backorder_1
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
        self.assertEqual(len(backorder_2.move_ids), 6)
        move_comp_e = backorder_2.move_ids.filtered(lambda m: m.product_id.id == self.component_e.id)
        self.assertFalse(move_comp_e)
        self._assert_quantities(backorder_2.move_ids, expected_quantities)

        # Process enough components to make x3 kit_parents
        qty_to_process = {
            self.component_a: 16,
            self.component_b: 5,
            self.component_c: 24,
            self.component_g: 5
        }
        self._process_quantities(backorder_2.move_ids, qty_to_process)

        # Create a backorder for the missing componenents
        wiz_act = backorder_2.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # Check that x3 kit_parents are indeed delivered
        self.assertEqual(order_line.qty_delivered, 3)

        # Check that the third backorder is created
        self.assertEqual(len(so.picking_ids), 4)
        backorder_3 = so.picking_ids - (picking_original + backorder_1 + backorder_2)
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
        self._assert_quantities(backorder_3.move_ids, expected_quantities)

        # Process all missing components
        self._process_quantities(backorder_3.move_ids, expected_quantities)

        # Validating the last backorder now it's complete.
        # All kits should be delivered
        backorder_3.button_validate()
        self.assertEqual(order_line.qty_delivered, 7.0)

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
        return_pick.button_validate()

        # Now quantity delivered should be 3 again
        self.assertEqual(order_line.qty_delivered, 3)

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_pick.ids, active_id=return_pick.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for move in return_wiz.product_return_moves:
            move.quantity = expected_quantities[move.product_id]
        res = return_wiz.create_returns()
        return_of_return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components except one of each
        for move in return_of_return_pick.move_ids:
            move.write({
                'quantity': expected_quantities[move.product_id] - 1,
                'picked': True,
                'to_refund': True
            })

        wiz_act = return_of_return_pick.button_validate()
        Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save().process()

        # As one of each component is missing, only 6 kit_parents should be delivered
        self.assertEqual(order_line.qty_delivered, 6)

        # Check that the 4th backorder is created.
        self.assertEqual(len(so.picking_ids), 7)
        backorder_4 = so.picking_ids - (picking_original + backorder_1 + backorder_2 + backorder_3 + return_of_return_pick + return_pick)
        self.assertEqual(backorder_4.backorder_id.id, return_of_return_pick.id)

        # Check the components quantities that backorder_4 should have
        for move in backorder_4.move_ids:
            self.assertEqual(move.product_qty, 1)

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
        f.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
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
        self.assertEqual(kit_parent_wh_order.virtual_available, 0)
        self.env.invalidate_all()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse=warehouse_1.id)
        self.assertEqual(kit_parent_wh1.virtual_available, 1)

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
        self.assertEqual(kit_parent_wh_order.virtual_available, 3)
        self.env.invalidate_all()
        kit_parent_wh1 = self.kit_parent.with_context(warehouse=warehouse_1.id)
        self.assertEqual(kit_parent_wh1.virtual_available, 1)

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
        self.assertEqual(kit_parent_wh_order.virtual_available, 7)

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
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(component_uom_unit, stock_location, 240)
        self.env['stock.quant']._update_available_quantity(component_uom_dozen, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(component_uom_kg, stock_location, 0.03)

        # Creation of a sale order for x10 kit_1
        partner = self.env['res.partner'].create({'name': 'My Test Partner'})
        f = Form(self.env['sale.order'])
        f.partner_id = partner
        with f.order_line.new() as line:
            line.product_id = kit_uom_1
            line.product_uom_qty = 10.0

        so = f.save()
        so.action_confirm()

        picking_original = so.picking_ids[0]
        move_ids = picking_original.move_ids
        order_line = so.order_line[0]

        # Check that the quantities on the picking are the one expected for each components
        for move in move_ids:
            corr_bom_line = bom_kit_uom_1.bom_line_ids.filtered(lambda b: b.product_id.id == move.product_id.id)
            computed_qty = move.product_uom._compute_quantity(move.product_uom_qty, corr_bom_line.product_uom_id)
            self.assertEqual(computed_qty, order_line.product_uom_qty * corr_bom_line.product_qty)

        # Processe enough componenents in the picking to make 2 kit_uom_1
        # Then create a backorder for the missing components
        qty_to_process = {
            component_uom_unit: 48,
            component_uom_dozen: 3,
            component_uom_kg: 0.006
        }
        self._process_quantities(move_ids, qty_to_process)
        res = move_ids.picking_id.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        # Check that a backorder is created
        self.assertEqual(len(so.picking_ids), 2)
        backorder_1 = so.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        # Only 2 kits should be delivered
        self.assertEqual(order_line.qty_delivered, 2)

        # Adding missing components
        qty_to_process = {
            component_uom_unit: 192,
            component_uom_dozen: 7,
            component_uom_kg: 0.024
        }
        self._process_quantities(backorder_1.move_ids, qty_to_process)

        # Validating the last backorder now it's complete
        backorder_1.button_validate()
        order_line._compute_qty_delivered()
        # All kits should be delivered
        self.assertEqual(order_line.qty_delivered, 10)

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
        #                                                       |- component_uom_kg      x5 Test-G

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
            'product_qty': 5.0,
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
        self.env['stock.quant']._update_available_quantity(component_uom_kg, warehouse_1.lot_stock_id, 0.12)
        self.env['stock.quant']._update_available_quantity(component_uom_gm, warehouse_1.lot_stock_id, 3000)

        # Creation of a sale order for x5 kit_uom_in_kit
        qty_ordered = 5
        f = Form(self.env['sale.order'])
        f.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
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
        self.assertEqual(virtual_available_wh_order, 1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)

        # We receive enough of each component in Warehouse 1 to make 3 kit_uom_in_kit.
        # Moves are created instead of only updating the quant quantities in order to trigger every compute fields.
        qty_to_process = {
            component_uom_unit: (1152, self.uom_unit),
            component_uom_dozen: (48, self.uom_dozen),
            component_uom_kg: (0.24, self.uom_kg),
            component_uom_gm: (6000, self.uom_gm)
        }
        self._create_move_quantities(qty_to_process, components, warehouse_1)

        # Check there arn't enough quantities available for the sale order
        self.assertTrue(float_compare(order_line.virtual_available_at_date - order_line.product_uom_qty, 0, precision_rounding=line.product_uom.rounding) == -1)
        kit_uom_in_kit.with_context(warehouse=warehouse_1.id)._compute_quantities()
        virtual_available_wh_order = kit_uom_in_kit.virtual_available
        self.assertEqual(virtual_available_wh_order, 3)

        # We process enough quantities to have enough kit_uom_in_kit available for the sale order.
        self._create_move_quantities(qty_to_process, components, warehouse_1)

        # We check that enough quantities were processed to sell 5 kit_uom_in_kit
        kit_uom_in_kit.with_context(warehouse=warehouse_1.id)._compute_quantities()
        self.assertEqual(kit_uom_in_kit.virtual_available, 5)

    def test_10_sale_mrp_kits_routes(self):

        # Create a kit 'kit_1' :
        # -----------------------
        #
        # kit_1 --|- component_shelf1   x3
        #         |- component_shelf2   x2

        stock_location_components = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        })
        stock_location_14 = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        })

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
        route_shelf1 = self.env['stock.route'].create({
            'name': 'Shelf1 -> Customer',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Shelf1 -> Customer',
                'action': 'pull',
                'picking_type_id': self.company_data['default_warehouse'].in_type_id.id,
                'location_src_id': stock_location_components.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })

        route_shelf2 = self.env['stock.route'].create({
            'name': 'Shelf2 -> Customer',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Shelf2 -> Customer',
                'action': 'pull',
                'picking_type_id': self.company_data['default_warehouse'].in_type_id.id,
                'location_src_id': stock_location_14.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })

        component_shelf1.write({
            'route_ids': [(4, route_shelf1.id)]})
        component_shelf2.write({
            'route_ids': [(4, route_shelf2.id)]})

        # Set enough quantities to make 1 kit_uom_in_kit in WH1
        self.env['stock.quant']._update_available_quantity(component_shelf1, self.company_data['default_warehouse'].lot_stock_id, 15)
        self.env['stock.quant']._update_available_quantity(component_shelf2, self.company_data['default_warehouse'].lot_stock_id, 10)

        # Creating a sale order for 5 kits and confirming it
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        with order_form.order_line.new() as line:
            line.product_id = kit_1
            line.product_uom = self.uom_unit
            line.product_uom_qty = 5
        order = order_form.save()
        order.action_confirm()

        # Now we check that the routes of the components were applied, in order to make sure the routes set
        # on the kit itself are ignored
        self.assertEqual(len(order.picking_ids), 2)
        self.assertEqual(len(order.picking_ids[0].move_ids), 1)
        self.assertEqual(len(order.picking_ids[1].move_ids), 1)
        moves = order.picking_ids.move_ids
        move_shelf1 = moves.filtered(lambda m: m.product_id == component_shelf1)
        move_shelf2 = moves.filtered(lambda m: m.product_id == component_shelf2)
        self.assertEqual(move_shelf1.location_id.id, stock_location_components.id)
        self.assertEqual(move_shelf1.location_dest_id.id, self.ref('stock.stock_location_customers'))
        self.assertEqual(move_shelf2.location_id.id, stock_location_14.id)
        self.assertEqual(move_shelf2.location_dest_id.id, self.ref('stock.stock_location_customers'))

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
        order_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        order_form.warehouse_id = warehouse_1
        with order_form.order_line.new() as line:
            line.product_id = kit_1
            line.product_uom = self.uom_unit
            line.product_uom_qty = 2
        order = order_form.save()
        order.action_confirm()

        # Now we check that the routes of the components were applied, in order to make sure the routes set
        # on the kit itself are ignored
        self.assertEqual(len(order.picking_ids), 1)
        self.assertEqual(len(order.picking_ids[0].move_ids), 2)

        # Finally, we check the quantities for each component on the picking
        move_component_unit = order.picking_ids[0].move_ids.filtered(lambda m: m.product_id == component_unit)
        move_component_kg = order.picking_ids[0].move_ids - move_component_unit
        self.assertEqual(move_component_unit.product_uom_qty, 0.5)
        self.assertEqual(move_component_kg.product_uom_qty, 0.58)

    def test_product_type_service_1(self):
        route_manufacture = self.company_data['default_warehouse'].manufacture_pull_id.route_id.id
        route_mto = self.company_data['default_warehouse'].mto_pull_id.route_id.id
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
        sale_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        with sale_form.order_line.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_uom_qty = 1.0
            line.product_uom = self.uom_unit
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])

        self.assertTrue(mo, 'Manufacturing order created.')

    def test_cancel_flow_1(self):
        """ Sell a MTO/manufacture product.

        Cancel the delivery and the production order. Then duplicate
        the delivery. Another production order should be created."""
        route_manufacture = self.company_data['default_warehouse'].manufacture_pull_id.route_id.id
        route_mto = self.company_data['default_warehouse'].mto_pull_id.route_id.id
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Create finished product
        finished_product = self.env['product.product'].create({
            'name': 'Geyser',
            'type': 'product',
            'route_ids': [(4, route_mto), (4, route_manufacture)],
        })

        product_raw = self.env['product.product'].create({
            'name': 'raw Geyser',
            'type': 'product',
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
        sale_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        with sale_form.order_line.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_uom_qty = 1.0
            line.product_uom = self.uom_unit
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])
        delivery = sale_order.picking_ids
        delivery.action_cancel()
        mo.action_cancel()
        copied_delivery = delivery.copy()
        copied_delivery.action_confirm()
        mos = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])
        self.assertEqual(len(mos), 1)
        self.assertEqual(mos.state, 'cancel')

    def test_cancel_flow_2(self):
        """ Sell a MTO/manufacture product.

        Cancel the production order and the delivery. Then duplicate
        the delivery. Another production order should be created."""
        route_manufacture = self.company_data['default_warehouse'].manufacture_pull_id.route_id.id
        route_mto = self.company_data['default_warehouse'].mto_pull_id.route_id.id
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Create finished product
        finished_product = self.env['product.product'].create({
            'name': 'Geyser',
            'type': 'product',
            'route_ids': [(4, route_mto), (4, route_manufacture)],
        })

        product_raw = self.env['product.product'].create({
            'name': 'raw Geyser',
            'type': 'product',
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
        sale_form.partner_id = self.env['res.partner'].create({'name': 'My Test Partner'})
        with sale_form.order_line.new() as line:
            line.name = finished_product.name
            line.product_id = finished_product
            line.product_uom_qty = 1.0
            line.product_uom = self.uom_unit
            line.price_unit = 10.0
        sale_order = sale_form.save()

        sale_order.action_confirm()

        mo = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])
        delivery = sale_order.picking_ids
        mo.action_cancel()
        delivery.action_cancel()
        copied_delivery = delivery.copy()
        copied_delivery.action_confirm()
        mos = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])
        self.assertEqual(len(mos), 1)
        self.assertEqual(mos.state, 'cancel')

    def test_13_so_return_kit(self):
        """
        Test that when returning a SO containing only a kit that contains another kit, the
        SO delivered quantities is set to 0 (with the all-or-nothing policy).
        Products :
            Main Kit
            Nested Kit
            Screw
        BoMs :
            Main Kit BoM (kit), recipe :
                Nested Kit Bom (kit), recipe :
                    Screw
        Business flow :
            Create those
            Create a Sales order selling one Main Kit BoM
            Confirm the sales order
            Validate the delivery (outgoing) (qty_delivered = 1)
            Create a return for the delivery
            Validate return for delivery (ingoing) (qty_delivered = 0)
        """
        main_kit_product = self.env['product.product'].create({
            'name': 'Main Kit',
            'type': 'product',
        })

        nested_kit_product = self.env['product.product'].create({
            'name': 'Nested Kit',
            'type': 'product',
        })

        product = self.env['product.product'].create({
            'name': 'Screw',
            'type': 'product',
        })

        self.env['mrp.bom'].create({
            'product_id': nested_kit_product.id,
            'product_tmpl_id': nested_kit_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': product.id})]
        })

        self.env['mrp.bom'].create({
            'product_id': main_kit_product.id,
            'product_tmpl_id': main_kit_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': nested_kit_product.id})]
        })

        # Create a SO for product Main Kit Product
        order_form = Form(self.env['sale.order'])
        order_form.partner_id = self.env['res.partner'].create({'name': 'Test Partner'})
        with order_form.order_line.new() as line:
            line.product_id = main_kit_product
            line.product_uom_qty = 1
        order = order_form.save()
        order.action_confirm()
        qty_del_not_yet_validated = sum(sol.qty_delivered for sol in order.order_line)
        self.assertEqual(qty_del_not_yet_validated, 0.0, 'No delivery validated yet')

        # Validate delivery
        pick = order.picking_ids
        pick.move_ids.write({'quantity': 1, 'picked': True})
        pick.button_validate()
        qty_del_validated = sum(sol.qty_delivered for sol in order.order_line)
        self.assertEqual(qty_del_validated, 1.0, 'The order went from warehouse to client, so it has been delivered')

        # 1 was delivered, now create a return
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=pick.ids, active_id=pick.ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 1,
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        return_pick.move_line_ids.quantity = 1
        return_pick.button_validate()  # validate return

        # Delivered quantities to the client should be 0
        qty_del_return_validated = sum(sol.qty_delivered for sol in order.order_line)
        self.assertNotEqual(qty_del_return_validated, 1.0, "The return was validated, therefore the delivery from client to"
                                                           " company was successful, and the client is left without his 1 product.")
        self.assertEqual(qty_del_return_validated, 0.0, "The return has processed, client doesn't have any quantity anymore")

    def test_14_change_bom_type(self):
        """ This test ensures that updating a Bom type during a flow does not lead to any error """
        p1 = self._cls_create_product('Master', self.uom_unit)
        p2 = self._cls_create_product('Component', self.uom_unit)
        p3 = self.component_a
        p1.categ_id.write({
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
        })
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 1)

        self.env['mrp.bom'].create({
            'product_tmpl_id': p1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': p2.id,
                'product_qty': 1.0,
            })]
        })

        p2_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': p2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': p3.id,
                'product_qty': 1.0,
            })]
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env['res.partner'].create({'name': 'Super Partner'})
        with so_form.order_line.new() as so_line:
            so_line.product_id = p1
        so = so_form.save()
        so.action_confirm()

        so.picking_ids.button_validate()

        p2_bom.type = "normal"

        so._create_invoices()
        invoice = so.invoice_ids
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def test_15_anglo_saxon_variant_price_unit(self):
        """
        Test the price unit of a variant from which template has another variant with kit bom.
        Products:
            Template A
                variant NOKIT
                variant KIT:
                    Component A
        Business Flow:
            create products and kit
            create SO selling both variants
            validate the delivery
            create the invoice
            post the invoice
        """

        # Create environment
        self.env.company.currency_id = self.env.ref('base.USD')
        self.env.company.anglo_saxon_accounting = True
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category', 'property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00', 'account_type': 'asset_receivable', 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00', 'account_type': 'liability_current', 'reconcile': True})
        account_income = self.env['account.account'].create({'name': 'Income', 'code': 'INC00', 'account_type': 'asset_current', 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00', 'account_type': 'liability_current', 'reconcile': True})
        account_valuation = self.env['account.account'].create({'name': 'Valuation', 'code': 'STV00', 'account_type': 'asset_receivable', 'reconcile': True})
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.partner.property_account_receivable_id = account_receiv
        self.category.property_account_income_categ_id = account_income
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = account_receiv
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = account_valuation

        # Create variant attributes
        self.prod_att_test = self.env['product.attribute'].create({'name': 'test'})
        self.prod_attr_KIT = self.env['product.attribute.value'].create({'name': 'KIT', 'attribute_id': self.prod_att_test.id, 'sequence': 1})
        self.prod_attr_NOKIT = self.env['product.attribute.value'].create({'name': 'NOKIT', 'attribute_id': self.prod_att_test.id, 'sequence': 2})

        # Create the template
        self.product_template = self.env['product.template'].create({
            'name': 'Template A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'invoice_policy': 'delivery',
            'categ_id': self.category.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_test.id,
                'value_ids': [(6, 0, [self.prod_attr_KIT.id, self.prod_attr_NOKIT.id])]
            })]
        })

        # Create the variants
        self.pt_attr_KIT = self.product_template.attribute_line_ids[0].product_template_value_ids[0]
        self.pt_attr_NOKIT = self.product_template.attribute_line_ids[0].product_template_value_ids[1]
        self.variant_KIT = self.product_template._get_variant_for_combination(self.pt_attr_KIT)
        self.variant_NOKIT = self.product_template._get_variant_for_combination(self.pt_attr_NOKIT)
        # Assign a cost to the NOKIT variant
        self.variant_NOKIT.write({'standard_price': 25})

        # Create the components
        self.comp_kit_a = self.env['product.product'].create({
            'name': 'Component Kit A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'categ_id': self.category.id,
            'standard_price': 20
        })
        self.comp_kit_b = self.env['product.product'].create({
            'name': 'Component Kit B',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'categ_id': self.category.id,
            'standard_price': 10
        })

        # Create the bom
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_template.id,
            'product_id': self.variant_KIT.id,
            'product_qty': 1.0,
            'type': 'phantom'
        })
        self.env['mrp.bom.line'].create({
            'product_id': self.comp_kit_a.id,
            'product_qty': 2.0,
            'bom_id': bom.id
        })
        self.env['mrp.bom.line'].create({
            'product_id': self.comp_kit_b.id,
            'product_qty': 1.0,
            'bom_id': bom.id
        })

        # Create the quants
        self.env['stock.quant']._update_available_quantity(self.variant_KIT, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.comp_kit_a, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.comp_kit_b, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.variant_NOKIT, self.stock_location, 1)

        # Create the sale order
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.variant_KIT.name,
                'product_id': self.variant_KIT.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'price_unit': 100,
            }), (0, 0, {
                'name': self.variant_NOKIT.name,
                'product_id': self.variant_NOKIT.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'price_unit': 50
            })],
            'company_id': self.env.company.id
        }
        so = self.env['sale.order'].create(so_vals)
        # Validate the sale order
        so.action_confirm()
        # Deliver the products
        pick = so.picking_ids
        pick.button_validate()
        # Create the invoice
        so._create_invoices()
        # Validate the invoice
        invoice = so.invoice_ids
        invoice.action_post()

        amls = invoice.line_ids
        aml_kit_expense = amls.filtered(lambda l: l.display_type == 'cogs' and l.debit > 0 and l.product_id == self.variant_KIT)
        aml_kit_output = amls.filtered(lambda l: l.display_type == 'cogs' and l.credit > 0 and l.product_id == self.variant_KIT)
        aml_nokit_expense = amls.filtered(lambda l: l.display_type == 'cogs' and l.debit > 0 and l.product_id == self.variant_NOKIT)
        aml_nokit_output = amls.filtered(lambda l: l.display_type == 'cogs' and l.credit > 0 and l.product_id == self.variant_NOKIT)

        # Check that the Cost of Goods Sold for variant KIT is equal to (2*20)+10 = 50
        self.assertEqual(aml_kit_expense.debit, 50, "Cost of Good Sold entry missing or mismatching for variant with kit")
        self.assertEqual(aml_kit_output.credit, 50, "Cost of Good Sold entry missing or mismatching for variant with kit")
        # Check that the Cost of Goods Sold for variant NOKIT is equal to its standard_price = 25
        self.assertEqual(aml_nokit_expense.debit, 25, "Cost of Good Sold entry missing or mismatching for variant without kit")
        self.assertEqual(aml_nokit_output.credit, 25, "Cost of Good Sold entry missing or mismatching for variant without kit")

    def test_16_anglo_saxon_variant_price_unit_multi_company(self):
        """
        Test the price unit of the BOM of the stock move is taken
        Products:
            Template A
                variant KIT 1
                variant KIT 2
        Business Flow:
            create SO
            validate the delivery
            archive the BOM and create a new one
            create the invoice
            post the invoice
        """

        # Create environment
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category', 'property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00', 'account_type': 'asset_receivable', 'reconcile': True})
        account_income = self.env['account.account'].create({'name': 'Income', 'code': 'INC00', 'account_type': 'asset_current', 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00', 'account_type': 'liability_current', 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00', 'account_type': 'liability_current', 'reconcile': True})
        account_valuation = self.env['account.account'].create({'name': 'Valuation', 'code': 'STV00', 'account_type': 'asset_receivable', 'reconcile': True})
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.partner.property_account_receivable_id = account_receiv
        self.category.property_account_income_categ_id = account_income
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = account_income
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = account_valuation

        # Create variant attributes
        self.prod_att_test = self.env['product.attribute'].create({'name': 'test'})
        self.prod_attr_KIT_A = self.env['product.attribute.value'].create({'name': 'KIT A', 'attribute_id': self.prod_att_test.id, 'sequence': 1})

        # Create the template
        self.product_template = self.env['product.template'].create({
            'name': 'Template A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'invoice_policy': 'delivery',
            'categ_id': self.category.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_test.id,
                'value_ids': [(6, 0, [self.prod_attr_KIT_A.id])]
            })]
        })

        # Create another variant
        self.pt_attr_KIT_A = self.product_template.attribute_line_ids[0].product_template_value_ids[0]
        self.variant_KIT_A = self.product_template._get_variant_for_combination(self.pt_attr_KIT_A)
        # Assign a cost to the NOKIT variant
        self.variant_KIT_A.write({'standard_price': 25})

        # Create the components
        self.comp_kit_a = self.env['product.product'].create({
            'name': 'Component Kit A',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'categ_id': self.category.id,
            'standard_price': 20
        })
        self.comp_kit_b = self.env['product.product'].create({
            'name': 'Component Kit B',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'categ_id': self.category.id,
            'standard_price': 10
        })

        # Create the bom
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_template.id,
            'product_id': self.variant_KIT_A.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'company_id': self.env.company.id,
        })
        self.env['mrp.bom.line'].create({
            'product_id': self.comp_kit_a.id,
            'product_qty': 1.0,
            'company_id': self.env.company.id,
            'bom_id': bom.id
        })

        # Create the quants
        self.env['stock.quant']._update_available_quantity(self.comp_kit_a, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.comp_kit_b, self.stock_location, 1)

        # Create the sale order
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.variant_KIT_A.name,
                'product_id': self.variant_KIT_A.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'price_unit': 50
            })],
            'company_id': self.env.company.id,
        }
        so = self.env['sale.order'].create(so_vals)
        # Validate the sale order
        so.action_confirm()
        # Deliver the products
        pick = so.picking_ids
        pick.button_validate()
        # archive bOM and update it
        bom.active = False
        bom_updated = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_template.id,
            'product_id': self.variant_KIT_A.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'company_id': self.env.company.id,
        })
        self.env['mrp.bom.line'].create({
            'product_id': self.comp_kit_b.id,
            'product_qty': 1.0,
            'company_id': self.env.company.id,
            'bom_id': bom_updated.id
        })

        # Create the invoice
        so._create_invoices()
        # Validate the invoice
        invoice = so.invoice_ids
        invoice.action_post()

        amls = invoice.line_ids
        aml_nokit_expense = amls.filtered(lambda l: l.display_type == 'cogs' and l.debit > 0 and l.product_id == self.variant_KIT_A)
        aml_nokit_output = amls.filtered(lambda l: l.display_type == 'cogs' and l.credit > 0 and l.product_id == self.variant_KIT_A)

        # Check that the Cost of Goods Sold for variant NOKIT is equal to the cost of the first BOM
        self.assertEqual(aml_nokit_expense.debit, 20, "Cost of Good Sold entry missing or mismatching for variant without kit")
        self.assertEqual(aml_nokit_output.credit, 20, "Cost of Good Sold entry missing or mismatching for variant without kit")

    def test_reconfirm_cancelled_kit(self):
        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [
                (0, 0, {
                    'name': self.kit_1.name,
                    'product_id': self.kit_1.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 1.0,
                })
            ],
        })

        # Updating the quantities in stock to prevent a 'Not enough inventory' warning message.
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_c, stock_location, 10)

        so.action_confirm()
        # Check picking creation
        self.assertEqual(len(so.picking_ids), 1, "A picking should be created after the SO validation")

        so.picking_ids.button_validate()

        so._action_cancel()
        so.action_draft()
        so.action_confirm()
        self.assertEqual(len(so.picking_ids), 1, "The product was already delivered, no need to re-create a delivery order")

    def test_kit_margin_and_return_picking(self):
        """ This test ensure that, when returning the components of a sold kit, the
        sale order line cost does not change"""
        kit = self._cls_create_product('Super Kit', self.uom_unit)
        (kit + self.component_a).categ_id.property_cost_method = 'fifo'

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': self.component_a.id,
                'product_qty': 1.0,
            })]
        })

        self.component_a.standard_price = 10
        kit.button_bom_cost()

        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 1)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = kit
        so = so_form.save()
        so.action_confirm()

        line = so.order_line
        price = line.product_id.with_company(line.company_id)._compute_average_price(0, line.product_uom_qty, line.move_ids)
        self.assertEqual(price, 10)

        picking = so.picking_ids
        picking.button_validate()

        ctx = {'active_ids':picking.ids, 'active_id': picking.ids[0], 'active_model': 'stock.picking'}
        return_picking_wizard_form = Form(self.env['stock.return.picking'].with_context(ctx))
        return_picking_wizard = return_picking_wizard_form.save()
        return_picking_wizard.create_returns()

        price = line.product_id.with_company(line.company_id)._compute_average_price(0, line.product_uom_qty, line.move_ids)
        self.assertEqual(price, 10)

    def test_kit_decrease_sol_qty(self):
        """
        Create and confirm a SO with a qty. Increasing/Decreasing the SOL qty
        should update the qty on the delivery. Then, process the delivery, make
        a return and adapt the SOL qty -> there should not be any new picking
        """
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        custo_location = self.env.ref('stock.stock_location_customers')

        grp_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})

        # 100 kit_3 = 100 x compo_f + 200 x compo_g
        self.env['stock.quant']._update_available_quantity(self.component_f, stock_location, 100)
        self.env['stock.quant']._update_available_quantity(self.component_g, stock_location, 200)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = self.kit_3
            line.product_uom_qty = 7
            line.product_uom = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        delivery = so.picking_ids
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.component_f.id, 'product_uom_qty': 70},
            {'product_id': self.component_g.id, 'product_uom_qty': 140},
        ])

        # Decrease
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 6
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.component_f.id, 'product_uom_qty': 60},
            {'product_id': self.component_g.id, 'product_uom_qty': 120},
        ])

        # Increase
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 10
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.component_f.id, 'product_uom_qty': 100},
            {'product_id': self.component_g.id, 'product_uom_qty': 200},
        ])
        delivery.button_validate()

        # Return 2 [uom_ten] x kit_3
        return_wizard_form = Form(self.env['stock.return.picking'].with_context(active_ids=delivery.ids, active_id=delivery.id, active_model='stock.picking'))
        return_wizard = return_wizard_form.save()
        return_wizard.product_return_moves[0].quantity = 20
        return_wizard.product_return_moves[1].quantity = 40
        action = return_wizard.create_returns()
        return_picking = self.env['stock.picking'].browse(action['res_id'])
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        # Adapt the SOL qty according to the delivered one
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 8

        self.assertRecordValues(so.picking_ids.sorted('id').move_ids, [
            {'product_id': self.component_f.id, 'location_dest_id': custo_location.id, 'quantity': 100, 'state': 'done'},
            {'product_id': self.component_g.id, 'location_dest_id': custo_location.id, 'quantity': 200, 'state': 'done'},
            {'product_id': self.component_f.id, 'location_dest_id': stock_location.id, 'quantity': 20, 'state': 'done'},
            {'product_id': self.component_g.id, 'location_dest_id': stock_location.id, 'quantity': 40, 'state': 'done'},
        ])

    def test_kit_decrease_sol_qty_to_zero(self):
        """
        Create and confirm a SO with a kit product. Increasing/Decreasing the SOL qty
        should update the qty on the delivery.
        """
        stock_location = self.company_data['default_warehouse'].lot_stock_id

        grp_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})

        # 10 kit_3 = 10 x compo_f + 20 x compo_g
        self.env['stock.quant']._update_available_quantity(self.component_f, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_g, stock_location, 20)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = self.kit_3
            line.product_uom_qty = 2
            line.product_uom = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        delivery = so.picking_ids
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.component_f.id, 'product_uom_qty': 20},
            {'product_id': self.component_g.id, 'product_uom_qty': 40},
        ])

        # Decrease the qty to 0
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 0
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.component_f.id, 'product_uom_qty': 0},
            {'product_id': self.component_g.id, 'product_uom_qty': 0},
        ])

    def test_kit_return_and_decrease_sol_qty_to_zero(self):
        """
        Create and confirm a SO with a kit product.
        Deliver & Return the components
        Set the SOL qty to 0
        """
        stock_location = self.company_data['default_warehouse'].lot_stock_id

        grp_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})

        # 10 kit_3 = 10 x compo_f + 20 x compo_g
        self.env['stock.quant']._update_available_quantity(self.component_f, stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.component_g, stock_location, 20)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = self.kit_3
            line.product_uom_qty = 2
            line.product_uom = self.uom_ten
        so = so_form.save()
        so.action_confirm()

        delivery = so.picking_ids
        for m in delivery.move_ids:
            m.write({'quantity': m.product_uom_qty, 'picked': True})
        delivery.button_validate()

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(so.order_line.qty_delivered, 2)

        ctx = {'active_id': delivery.id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_picking_id, dummy = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_picking_id)
        for m in return_picking.move_ids:
            m.write({'quantity': m.product_uom_qty, 'picked': True})
        return_picking.button_validate()

        self.assertEqual(return_picking.state, 'done')
        self.assertEqual(so.order_line.qty_delivered, 0)

        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 0

        self.assertEqual(so.picking_ids, delivery | return_picking)

    def test_fifo_reverse_and_create_new_invoice(self):
        """
        FIFO automated
        Kit with one component
        Receive the component: 1@10, 1@50
        Deliver 1 kit
        Post the invoice, add a credit note with option 'new draft inv'
        Post the second invoice
        COGS should be based on the delivered kit
        """
        kit = self._create_product('Simple Kit', self.uom_unit)
        categ_form = Form(self.env['product.category'])
        categ_form.name = 'Super Fifo'
        categ_form.property_cost_method = 'fifo'
        categ_form.property_valuation = 'real_time'
        categ = categ_form.save()
        (kit + self.component_a).categ_id = categ

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': self.component_a.id, 'product_qty': 1.0})]
        })

        in_moves = self.env['stock.move'].create([{
            'name': 'IN move @%s' % p,
            'product_id': self.component_a.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.component_a.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 50]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 1.0,
                    'product_uom': kit.uom_id.id,
                    'price_unit': 100,
                    'tax_id': False,
                })],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.write({'quantity': 1.0, 'picked': True})
        picking.button_validate()

        invoice01 = so._create_invoices()
        invoice01.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'journal_id': invoice01.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        invoice02 = self.env['account.move'].browse(reversal['res_id'])
        invoice02.action_post()

        amls = invoice02.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == categ.property_stock_account_output_categ_id)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == categ.property_account_expense_categ_id)
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)

    def test_kit_avco_amls_reconciliation(self):
        self.stock_account_product_categ.property_cost_method = 'average'

        compo01, compo02, kit = self.env['product.product'].create([{
            'name': name,
            'type': 'product',
            'standard_price': price,
            'categ_id': self.stock_account_product_categ.id,
            'invoice_policy': 'delivery',
        } for name, price in [
            ('Compo 01', 10),
            ('Compo 02', 20),
            ('Kit', 0),
        ]])

        self.env['stock.quant']._update_available_quantity(compo01, self.company_data['default_warehouse'].lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(compo02, self.company_data['default_warehouse'].lot_stock_id, 1)

        self.env['mrp.bom'].create({
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_uom_id': kit.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1.0}),
            ],
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 1.0,
                    'product_uom': kit.uom_id.id,
                    'price_unit': 5,
                    'tax_id': False,
                })],
        })
        so.action_confirm()
        so.picking_ids.move_line_ids.quantity = 1
        so.picking_ids.move_ids.picked = True
        so.picking_ids.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()

        self.assertEqual(len(invoice.line_ids.filtered('reconciled')), 1)

    def test_avoid_removing_kit_bom_in_use(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.kit_1.name,
                    'product_id': self.kit_1.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.kit_1.uom_id.id,
                    'price_unit': 5,
                    'tax_id': False,
                })],
        })
        self.bom_kit_1.toggle_active()
        self.bom_kit_1.toggle_active()

        so.action_confirm()
        with self.assertRaises(UserError):
            self.bom_kit_1.write({'type': 'normal'})
        with self.assertRaises(UserError):
            self.bom_kit_1.toggle_active()
        with self.assertRaises(UserError):
            self.bom_kit_1.unlink()

        for move in so.order_line.move_ids:
            move.write({'quantity': move.product_uom_qty, 'picked': True})
        so.picking_ids.button_validate()

        self.assertEqual(so.picking_ids.state, 'done')
        with self.assertRaises(UserError):
            self.bom_kit_1.write({'type': 'normal'})
        with self.assertRaises(UserError):
            self.bom_kit_1.toggle_active()
        with self.assertRaises(UserError):
            self.bom_kit_1.unlink()

        invoice = so._create_invoices()
        invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
        self.bom_kit_1.toggle_active()
        self.bom_kit_1.toggle_active()
        self.bom_kit_1.write({'type': 'normal'})
        self.bom_kit_1.write({'type': 'phantom'})
        self.bom_kit_1.unlink()

    def test_merge_move_kit_on_adding_new_sol(self):
        """
        Create and confirm an SO for 2 similar kit products.
        Add a new sale order line for an other unrelated prodcut.

        Check that the delivery kit moves were not merged by the confirmation of the new move.
        """
        # grp_uom = self.env.ref('uom.group_uom')
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_ship'
        kit = self.kit_3
        # create a similar kit
        bom_copy = kit.bom_ids[0].copy()
        kit_copy = kit.copy()
        bom_copy.product_tmpl_id = kit_copy.product_tmpl_id
        # put component in stock: 10 kit = 10 x comp_f + 20 x comp_g
        self.env['stock.quant']._update_available_quantity(self.component_f, warehouse.lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(self.component_g, warehouse.lot_stock_id, 20)
        self.env['stock.quant']._update_available_quantity(self.component_a, warehouse.lot_stock_id, 5)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = kit
            line.product_uom_qty = 2
        with so_form.order_line.new() as line:
            line.product_id = kit_copy
            line.product_uom_qty = 3
        so = so_form.save()
        so.action_confirm()

        pick = so.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pick_type_id)
        expected_pick_moves = [
            { 'quantity': 2.0, 'product_id': self.component_f.id, 'bom_line_id': kit.bom_ids[0].bom_line_ids.filtered(lambda bl: bl.product_id == self.component_f).id},
            { 'quantity': 3.0, 'product_id': self.component_f.id, 'bom_line_id': bom_copy.bom_line_ids.filtered(lambda bl: bl.product_id == self.component_f).id},
            { 'quantity': 4.0, 'product_id': self.component_g.id, 'bom_line_id': kit.bom_ids[0].bom_line_ids.filtered(lambda bl: bl.product_id == self.component_g).id},
            { 'quantity': 6.0, 'product_id': self.component_g.id, 'bom_line_id': bom_copy.bom_line_ids.filtered(lambda bl: bl.product_id == self.component_g).id},
        ]
        self.assertRecordValues(pick.move_ids.sorted(lambda m: m.quantity), expected_pick_moves)
        with Form(so) as so_form:
            with so_form.order_line.new() as line:
                line.product_id = self.component_a
                line.product_uom_qty = 1
        expected_pick_moves = [
            { 'quantity': 1.0, 'product_id': self.component_a.id, 'bom_line_id': False},
        ] + expected_pick_moves
        self.assertRecordValues(pick.move_ids.sorted(lambda m: m.quantity), expected_pick_moves)

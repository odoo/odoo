# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, Form, tagged


@tagged('post_install', '-at_install')
class TestSaleMrpKitBom(TransactionCase):

    def _create_product(self, name, product_type, price):
        return self.env['product.product'].create({
            'name': name,
            'type': product_type,
            'standard_price': price,
        })

    def test_reset_avco_kit(self):
        """
        Test a specific use case : One product with 2 variant, each variant has its own BoM with either component_1 or
        component_2. Create a SO for one of the variant, confirm, cancel, reset to draft and then change the product of
        the SO -> There should be no traceback
        """
        component_1 = self.env['product.product'].create({'name': 'compo 1'})
        component_2 = self.env['product.product'].create({'name': 'compo 2'})

        product_category = self.env['product.category'].create({
            'name': 'test avco kit',
            'property_cost_method': 'average'
        })
        attributes = self.env['product.attribute'].create({'name': 'Legs'})
        steel_legs = self.env['product.attribute.value'].create({'attribute_id': attributes.id, 'name': 'Steel'})
        aluminium_legs = self.env['product.attribute.value'].create(
            {'attribute_id': attributes.id, 'name': 'Aluminium'})

        product_template = self.env['product.template'].create({
            'name': 'test product',
            'categ_id': product_category.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attributes.id,
                'value_ids': [(6, 0, [steel_legs.id, aluminium_legs.id])]
            })]
        })
        product_variant_ids = product_template.product_variant_ids
        # BoM 1 with component_1
        self.env['mrp.bom'].create({
            'product_id': product_variant_ids[0].id,
            'product_tmpl_id': product_variant_ids[0].product_tmpl_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component_1.id, 'product_qty': 1})]
        })
        # BoM 2 with component_2
        self.env['mrp.bom'].create({
            'product_id': product_variant_ids[1].id,
            'product_tmpl_id': product_variant_ids[1].product_tmpl_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component_2.id, 'product_qty': 1})]
        })
        partner = self.env['res.partner'].create({'name': 'Testing Man'})
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        # Create the order line
        self.env['sale.order.line'].create({
            'name': "Order line",
            'product_id': product_variant_ids[0].id,
            'order_id': so.id,
        })
        so.action_confirm()
        so._action_cancel()
        so.action_draft()
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as order_line_change:
                # The actual test, there should be no traceback here
                order_line_change.product_id = product_variant_ids[1]

    def test_sale_mrp_kit_cost(self):
        """
         Check the total cost of a KIT:
            # BoM of Kit A:
                # - BoM Type: Kit
                # - Quantity: 1
                # - Components:
                # * 1 x Component A (Cost: $ 6, QTY: 1, UOM: Dozens)
                # * 1 x Component B (Cost: $ 10, QTY: 2, UOM: Unit)
            # cost of Kit A = (6 * 1 * 12) + (10 * 2) = $ 92
        """
        self.customer = self.env['res.partner'].create({
            'name': 'customer'
        })

        self.kit_product = self._create_product('Kit Product', 'product', 1.00)
        # Creating components
        self.component_a = self._create_product('Component A', 'product', 1.00)
        self.component_a.product_tmpl_id.standard_price = 6
        self.component_b = self._create_product('Component B', 'product', 1.00)
        self.component_b.product_tmpl_id.standard_price = 10

        cat = self.env['product.category'].create({
            'name': 'fifo',
            'property_cost_method': 'fifo'
        })
        self.kit_product.product_tmpl_id.categ_id = cat
        self.component_a.product_tmpl_id.categ_id = cat
        self.component_b.product_tmpl_id.categ_id = cat

        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom'
        })

        self.env['mrp.bom.line'].create({
                'product_id': self.component_a.id,
                'product_qty': 1.0,
                'bom_id': self.bom.id,
                'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
        })
        self.env['mrp.bom.line'].create({
                'product_id': self.component_b.id,
                'product_qty': 2.0,
                'bom_id': self.bom.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        # Create a SO with one unit of the kit product
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': self.kit_product.name,
                    'product_id': self.kit_product.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.kit_product.uom_id.id,
                })],
        })
        so.action_confirm()
        line = so.order_line
        purchase_price = line.product_id.with_company(line.company_id)._compute_average_price(0, line.product_uom_qty, line.move_ids)
        self.assertEqual(purchase_price, 92, "The purchase price must be the total cost of the components multiplied by their unit of measure")

    def test_qty_delivered_with_bom(self):
        """Check the quantity delivered, when a bom line has a non integer quantity"""

        self.env.ref('product.decimal_product_uom').digits = 5

        self.kit = self._create_product('Kit', 'product', 0.00)
        self.comp = self._create_product('Component', 'product', 0.00)

        # Create BoM for Kit
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp
            bom_line.product_qty = 0.08600
        self.bom = bom_product_form.save()


        self.customer = self.env['res.partner'].create({
            'name': 'customer',
        })

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': self.kit.name,
                    'product_id': self.kit.id,
                    'product_uom_qty': 10.0,
                    'product_uom': self.kit.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                })],
        })
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.order_line.qty_delivered, 0)

        picking = so.picking_ids
        picking.move_ids.quantity_done = 0.86000
        picking.button_validate()

        # Checks the delivery amount (must be 10).
        self.assertEqual(so.order_line.qty_delivered, 10)

    def test_qty_delivered_with_bom_using_kit(self):
        """Check the quantity delivered, when one product is a kit
        and his bom uses another product that is also a kit"""

        self.kitA = self._create_product('Kit A', 'consu', 0.00)
        self.kitB = self._create_product('Kit B', 'consu', 0.00)
        self.compA = self._create_product('ComponentA', 'consu', 0.00)
        self.compB = self._create_product('ComponentB', 'consu', 0.00)

        # Create BoM for KitB
        bom_product_formA = Form(self.env['mrp.bom'])
        bom_product_formA.product_id = self.kitB
        bom_product_formA.product_tmpl_id = self.kitB.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = 'phantom'
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compB
            bom_line.product_qty = 1
        self.bomA = bom_product_formA.save()

        # Create BoM for KitA
        bom_product_formB = Form(self.env['mrp.bom'])
        bom_product_formB.product_id = self.kitA
        bom_product_formB.product_tmpl_id = self.kitA.product_tmpl_id
        bom_product_formB.product_qty = 1.0
        bom_product_formB.type = 'phantom'
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compA
            bom_line.product_qty = 1
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.kitB
            bom_line.product_qty = 1
        self.bomB = bom_product_formB.save()

        self.customer = self.env['res.partner'].create({
            'name': 'customer',
        })

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': self.kitA.name,
                    'product_id': self.kitA.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.kitA.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                })],
        })
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.order_line.qty_delivered, 0)

        picking = so.picking_ids
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        # Checks the delivery amount (must be 1).
        self.assertEqual(so.order_line.qty_delivered, 1)

    def test_sale_kit_show_kit_in_delivery(self):
        """Create a kit with 2 product and activate 2 steps
            delivery and check that every stock move contains
            a bom_line_id
        """

        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        wh.write({'delivery_steps': 'pick_ship'})

        kitA = self._create_product('Kit Product', 'product', 0.00)
        compA = self._create_product('ComponentA', 'product', 0.00)
        compB = self._create_product('ComponentB', 'product', 0.00)

        # Create BoM for KitB
        bom_product_formA = Form(self.env['mrp.bom'])
        bom_product_formA.product_id = kitA
        bom_product_formA.product_tmpl_id = kitA.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = 'phantom'
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compB
            bom_line.product_qty = 1
        bom_product_formA.save()

        customer = self.env['res.partner'].create({
            'name': 'customer',
        })

        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                (0, 0, {
                    'name': kitA.name,
                    'product_id': kitA.id,
                    'product_uom_qty': 1.0,
                    'product_uom': kitA.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                })]
        })
        so.action_confirm()

        pick = so.picking_ids[0]
        ship = so.picking_ids[1]

        self.assertTrue(pick.move_ids_without_package[0].bom_line_id, "All component from kits should have a bom line")
        self.assertTrue(pick.move_ids_without_package[1].bom_line_id, "All component from kits should have a bom line")
        self.assertTrue(ship.move_ids_without_package[0].bom_line_id, "All component from kits should have a bom line")
        self.assertTrue(ship.move_ids_without_package[1].bom_line_id, "All component from kits should have a bom line")

    def test_qty_delivered_with_bom_using_kit2(self):
        """Create 2 kits products that have common components and activate 2 steps delivery
           Then create a sale order with these 2 products, and put everything in a pack in
           the first step of the delivery. After the shipping is done, check the done quantity
           is correct for each products.
        """

        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        wh.write({'delivery_steps': 'pick_ship'})

        kitAB = self._create_product('Kit AB', 'product', 0.00)
        kitABC = self._create_product('Kit ABC', 'product', 0.00)
        compA = self._create_product('ComponentA', 'product', 0.00)
        compB = self._create_product('ComponentB', 'product', 0.00)
        compC = self._create_product('ComponentC', 'product', 0.00)

        # Create BoM for KitB
        bom_product_formA = Form(self.env['mrp.bom'])
        bom_product_formA.product_id = kitAB
        bom_product_formA.product_tmpl_id = kitAB.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = 'phantom'
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compB
            bom_line.product_qty = 1
        bom_product_formA.save()

        # Create BoM for KitA
        bom_product_formB = Form(self.env['mrp.bom'])
        bom_product_formB.product_id = kitABC
        bom_product_formB.product_tmpl_id = kitABC.product_tmpl_id
        bom_product_formB.product_qty = 1.0
        bom_product_formB.type = 'phantom'
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = compA
            bom_line.product_qty = 1
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = compB
            bom_line.product_qty = 1
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = compC
            bom_line.product_qty = 1
        bom_product_formB.save()

        customer = self.env['res.partner'].create({
            'name': 'customer',
        })

        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                (0, 0, {
                    'name': kitAB.name,
                    'product_id': kitAB.id,
                    'product_uom_qty': 1.0,
                    'product_uom': kitAB.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                }),
                (0, 0, {
                    'name': kitABC.name,
                    'product_id': kitABC.id,
                    'product_uom_qty': 1.0,
                    'product_uom': kitABC.uom_id.id,
                    'price_unit': 1,
                    'tax_id': False,
                })],
        })
        so.action_confirm()

        pick = so.picking_ids[0]
        ship = so.picking_ids[1]

        for move in pick.move_ids:
            move.quantity_done = 1

        pick.action_put_in_pack()
        pick.button_validate()

        ship.package_level_ids.write({'is_done': True})
        ship.package_level_ids._set_is_done()

        for move_line in ship.move_line_ids:
            self.assertEqual(move_line.move_id.product_uom_qty, move_line.qty_done, "Quantity done should be equal to the quantity reserved in the move line")

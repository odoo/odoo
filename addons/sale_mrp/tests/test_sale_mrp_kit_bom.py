# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleMrpKitBom(TransactionCase):

    def _create_product(self, name, storable, price):
        return self.env['product.product'].create({
            'name': name,
            'is_storable': storable,
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

        self.kit_product = self._create_product('Kit Product', True, 1.00)
        # Creating components
        self.component_a = self._create_product('Component A', True, 1.00)
        self.component_a.product_tmpl_id.standard_price = 6
        self.component_b = self._create_product('Component B', True, 1.00)
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

    def test_sale_mrp_kit_sale_price(self):
        """Check the total sale price of a KIT:
            # BoM of Kit A:
                # - BoM Type: Kit
                # - Quantity: 1
                # - Components:
                # * 1 x Component A (Price: $ 8, QTY: 10, UOM: Meter)
                # * 1 x Component B (Price: $ 5, QTY: 2, UOM: Dozen)
            # sale price of Kit A = (8 * 10) + (5 * 2 * 12) = $ 200
        """
        if "sale_price" not in self.env["stock.move.line"]._fields:
            self.skipTest("This test only runs with both sale_mrp and stock_delivery installed")

        self.customer = self.env['res.partner'].create({
            'name': 'customer',
        })
        self.warehouse = self.env["stock.warehouse"].create({
            'name': 'Warehouse #2',
            'code': 'WH02',
        })

        self.kit_product = self._create_product('Kit Product', 'product', 1.00)
        # Creating components
        self.component_a = self._create_product('Component A', 'product', 1.00)
        self.component_a.uom_id = self.env.ref('uom.product_uom_meter').id
        self.component_a.product_tmpl_id.list_price = 8
        self.component_b = self._create_product('Component B', 'product', 1.00)
        self.component_b.product_tmpl_id.list_price = 5

        location_id = self.warehouse.lot_stock_id.id
        self.env["stock.quant"].with_context(inventory_mode=True).create([
            {"product_id": self.component_a.id, "inventory_quantity": 10, "location_id": location_id},
            {"product_id": self.component_b.id, "inventory_quantity": 24, "location_id": location_id},
        ]).action_apply_inventory()

        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.component_a.id,
                    'product_qty': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_meter').id,
                }),
                Command.create({
                    'product_id': self.component_b.id,
                    'product_qty': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                }),
            ]
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
            'warehouse_id': self.warehouse.id,
        })
        so.action_confirm()
        so.picking_ids._action_done()
        move_lines = so.picking_ids.move_ids.move_line_ids
        self.assertEqual(move_lines.mapped("sale_price"), [80, 120], 'wrong shipping value')

    def test_qty_delivered_with_bom(self):
        """Check the quantity delivered, when a bom line has a non integer quantity"""

        self.env.ref('product.decimal_product_uom').digits = 5

        self.kit = self._create_product('Kit', True, 0.00)
        self.comp = self._create_product('Component', True, 0.00)

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
        picking.move_ids.write({'quantity': 0.86000, 'picked': True})
        picking.button_validate()

        # Checks the delivery amount (must be 10).
        self.assertEqual(so.order_line.qty_delivered, 10)

    def test_qty_delivered_with_bom_using_kit(self):
        """Check the quantity delivered, when one product is a kit
        and his bom uses another product that is also a kit"""

        self.kitA = self._create_product('Kit A', False, 0.00)
        self.kitB = self._create_product('Kit B', False, 0.00)
        self.compA = self._create_product('ComponentA', False, 0.00)
        self.compB = self._create_product('ComponentB', False, 0.00)

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
        picking.button_validate()

        # Checks the delivery amount (must be 1).
        self.assertEqual(so.order_line.qty_delivered, 1)

    def test_sale_kit_show_kit_in_delivery(self):
        """Create a kit with 2 product and activate 2 steps
            delivery and check that every stock move contains
            a bom_line_id
        """

        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        wh.write({'delivery_steps': 'pick_ship'})

        kitA = self._create_product('Kit Product', True, 0.00)
        compA = self._create_product('ComponentA', True, 0.00)
        compB = self._create_product('ComponentB', True, 0.00)

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
        self.assertTrue(pick.move_ids_without_package[0].bom_line_id, "All component from kits should have a bom line")
        self.assertTrue(pick.move_ids_without_package[1].bom_line_id, "All component from kits should have a bom line")
        pick.move_ids.write({'quantity': 1, 'picked': True})
        pick.button_validate()

        ship = so.picking_ids[1]
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

        kitAB = self._create_product('Kit AB', True, 0.00)
        kitABC = self._create_product('Kit ABC', True, 0.00)
        compA = self._create_product('ComponentA', True, 0.00)
        compB = self._create_product('ComponentB', True, 0.00)
        compC = self._create_product('ComponentC', True, 0.00)

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
        for move in pick.move_ids:
            move.write({'quantity': 1, 'picked': True})

        pick.action_put_in_pack()
        pick.button_validate()

        ship = so.picking_ids[1]
        ship.package_level_ids.write({'is_done': True})
        ship.package_level_ids._set_is_done()

        for move_line in ship.move_line_ids:
            self.assertEqual(move_line.move_id.product_uom_qty, move_line.quantity, "Quantity done should be equal to the quantity reserved in the move line")

    def test_kit_in_delivery_slip(self):
        """
        Suppose this structure:
        Sale order:
            - Kit 1 with a sales description("test"):
                |- Compo 1
            - Product 1
            - Kit 2
                * Variant 1
                    - Compo 1
                * Variant 2
                    - Compo 1
            - Kit 4:
                - Compo 1
            - Kit 5
                - Kit 4
                - Compo 1

        This test ensures that, when delivering a Kit product with a sales description,
        the delivery report is correctly printed with all the products.
        """
        kit_1, component_1, product_1, kit_3, kit_4 = self.env['product.product'].create([{
            'name': n,
            'is_storable': True,
        } for n in ['Kit 1', 'Compo 1', 'Product 1', 'Kit 3', 'Kit 4']])
        kit_1.description_sale = "test"

        self.env['mrp.bom'].create([{
            'product_tmpl_id': kit_1.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
            ],
        }])
        colors = ['red', 'blue']
        prod_attr = self.env['product.attribute'].create({'name': 'Color', 'create_variant': 'always'})
        prod_attr_values = self.env['product.attribute.value'].create([{'name': color, 'attribute_id': prod_attr.id, 'sequence': 1} for color in colors])
        kit_2 = self.env['product.template'].create({
            'name': 'Kit 2',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': prod_attr.id,
                'value_ids': [(6, 0, prod_attr_values.ids)]
            })]
        })
        self.env['mrp.bom'].create([{
            'product_tmpl_id': kit_2.id,
            'product_id': kit_2.product_variant_ids[0].id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
            ],
        }])
        self.env['mrp.bom'].create([{
            'product_tmpl_id': kit_2.id,
            'product_id': kit_2.product_variant_ids[1].id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
            ],
        }])
        self.env['mrp.bom'].create([{
            'product_tmpl_id': kit_3.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
            ],
        }])
        self.env['mrp.bom'].create([{
            'product_tmpl_id': kit_4.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': kit_3.id, 'product_qty': 1}),
            ],
        }])
        customer = self.env['res.partner'].create({
            'name': 'customer',
        })
        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                (0, 0, {
                    'product_id': kit_1.id,
                    'product_uom_qty': 1.0,
                }),
                (0, 0, {
                    'product_id': product_1.id,
                    'product_uom_qty': 1.0,
                }),
                (0, 0, {
                    'product_id': kit_2.product_variant_ids[0].id,
                    'product_uom_qty': 1.0,
                }),
                (0, 0, {
                    'product_id': kit_2.product_variant_ids[1].id,
                    'product_uom_qty': 1.0,
                }),
                (0, 0, {
                    'product_id': kit_3.id,
                    'product_uom_qty': 1.0,
                }),
                (0, 0, {
                    'product_id': kit_4.id,
                    'product_uom_qty': 1.0,
                })],
        })
        so.action_confirm()
        picking = so.picking_ids
        self.assertEqual(len(so.picking_ids.move_ids_without_package), 7)
        picking.move_ids.write({'quantity': 1, 'picked': True})
        picking.button_validate()
        self.assertEqual(picking.state, 'done')

        html_report = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', picking.ids)[0].decode('utf-8').split('\n')
        keys = [
            "Kit 1", "Compo 1", "Kit 2 (red)", "Compo 1", "Kit 2 (blue)", "Compo 1",
            "Kit 3", "Compo 1", "Kit 4", "Compo 1",
            "Products not associated with a kit", "Product 1",
        ]
        for line in html_report:
            if not keys:
                break
            if keys[0] in line:
                keys = keys[1:]
        self.assertFalse(keys, "All keys should be in the report with the defined order")

    def test_sale_multistep_kit_qty_change(self):
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.write({'delivery_steps': 'pick_ship'})
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

        kit_prod = self._create_product('kit_prod', 'product', 0.00)
        sub_kit = self._create_product('sub_kit', 'product', 0.00)
        component = self._create_product('component', 'product', 0.00)
        component.uom_id = self.env.ref('uom.product_uom_dozen')
        self.env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, 30)
        # 6 kit_prod == 5 component
        self.env['mrp.bom'].create([{  # 2 kit_prod == 5 sub_kit
            'product_tmpl_id': kit_prod.product_tmpl_id.id,
            'product_qty': 2.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': sub_kit.id,
                'product_qty': 5,
            })],
        }, {  # 3 sub_kit == 1 component
            'product_tmpl_id': sub_kit.product_tmpl_id.id,
            'product_qty': 3.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': component.id,
                'product_qty': 1,
            })],
        }])

        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': kit_prod.name,
                'product_id': kit_prod.id,
                'product_uom_qty': 30,
            })],
        })
        # Validate the SO
        so.action_confirm()
        picking_pick = so.picking_ids[0]
        picking_pick.picking_type_id.create_backorder = 'never'

        # Check the component qty in the created picking should be 25
        self.assertEqual(picking_pick.move_ids.product_qty, 30 * 5 / 6)

        # Update the kit quantity in the SO
        so.order_line[0].product_uom_qty = 60
        # Check the component qty after the update should be 50
        self.assertEqual(picking_pick.move_ids.product_qty, 60 * 5 / 6)

        # Deliver half the quantity 25 component == 30 kit_prod
        picking_pick.move_ids.quantity = 25
        picking_pick.button_validate()

        picking_ship = so.picking_ids[1]
        picking_ship.picking_type_id.create_backorder = 'never'
        picking_ship.move_ids.quantity = 25
        picking_ship.button_validate()
        self.assertEqual(so.order_line.qty_delivered, 25 / 5 * 6)

        # Return 10 components
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_ship.ids, active_id=picking_ship.id,
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 10,
                'to_refund': True
            })
        res = return_wiz.action_create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Process all components and validate the return
        return_pick.button_validate()
        self.assertEqual(so.order_line.qty_delivered, 15 / 5 * 6)

        # Resend 5 components
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_pick.ids, active_id=return_pick.id,
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 5,
                'to_refund': True
            })
        res = return_wiz.action_create_returns()

        # Validate the return
        self.env['stock.picking'].browse(res['res_id']).button_validate()
        self.assertEqual(so.order_line.qty_delivered, 20 / 5 * 6)

    def test_sale_kit_qty_change(self):

        # Create record rule
        mrp_bom_model = self.env['ir.model']._get('mrp.bom')
        self.env['ir.rule'].create({
            'name': "No one allowed to access BoMs",
            'model_id': mrp_bom_model.id,
            'domain_force': [(0, '=', 1)],
        })

        # Create BoM
        kit_product = self._create_product('Kit Product', 'product', 1)
        component_a = self._create_product('Component A', 'product', 1)
        self.env['mrp.bom'].create({
            'product_id': kit_product.id,
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component_a.id, 'product_qty': 1})]
        })

        # Create sale order
        partner = self.env['res.partner'].create({'name': 'Testing Man'})
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'name': "Order line",
            'product_id': kit_product.id,
            'order_id': so.id,
        })
        so.action_confirm()

        user_admin = self.env['res.users'].search([('login', '=', 'admin')])
        sol.with_user(user_admin).write({'product_uom_qty': 5})

        self.assertEqual(sum(sol.move_ids.mapped('product_uom_qty')), 5)

    def test_sale_kit_with_mto_components_qty_change(self):
        """
        Check that updating the demand on a sale order line for a kit product
        updates the associated deliveries accordingly
        """
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        warehouse = self.env.ref('stock.warehouse0')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.toggle_active()
        manufacturing_route_id = self.ref('mrp.route_warehouse0_manufacture')
        kit_product, comp, mto_comp, subcomp = self.env['product.product'].create([
            {
                'name': 'kit_product',
                'is_storable': True,
                'route_ids': [],
            },
            {
                'name': 'component',
                'is_storable': True,
                'route_ids': [],
            },
            {
                'name': 'mto_component',
                'is_storable': True,
                'route_ids': [Command.set([mto_route.id, manufacturing_route_id])],
            },
            {
                'name': 'subcomponent',
                'is_storable': True,
                'route_ids': [],
            },
        ])
        self.env['stock.quant']._update_available_quantity(comp, warehouse.lot_stock_id, 30.0)
        self.env['mrp.bom'].create([
            {  # 2 kit_prod -> 5 comp and 3 mto_comp
                'product_tmpl_id': kit_product.product_tmpl_id.id,
                'product_qty': 2.0,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({'product_id': comp.id, 'product_qty': 5}),
                    Command.create({'product_id': mto_comp.id, 'product_qty': 3}),
                ],
            },
            {  # bom to manufacture mto_comp
                'product_tmpl_id': mto_comp.product_tmpl_id.id,
                'product_qty': 1.0,
                'bom_line_ids': [
                    Command.create({'product_id': subcomp.id, 'product_qty': 1}),
                ],
            }
        ])

        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'name': kit_product.name,
                    'product_id': kit_product.id,
                    'product_uom_qty': 4,
            })],
        })
        # confirm the SO and check the delivery
        so.action_confirm()
        self.assertRecordValues(so.picking_ids.move_ids.sorted('product_uom_qty'), [
            {'product_id': mto_comp.id, 'product_uom_qty': 6.0},
            {'product_id': comp.id, 'product_uom_qty': 10.0},
        ])
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 10
        # the moves assocaited to the mto component are expected to be separated as
        # the are linked to a different MO
        self.assertRecordValues(so.picking_ids.move_ids.sorted('product_uom_qty'), [
            {'product_id': mto_comp.id, 'product_uom_qty': 6.0},
            {'product_id': mto_comp.id, 'product_uom_qty': 9.0},
            {'product_id': comp.id, 'product_uom_qty': 25.0},
        ])

    def test_inter_company_qty_delivered_with_kit(self):
        """
        Test that the delivered quantity is updated on a sale order line when selling a kit
        through an inter-company transaction.
        """
        self.env.user.write({'groups_id': [(4, self.env.ref('base.group_multi_company').id)]})
        # Create the kit product and BoM
        kit_product = self._create_product('Kit', 'product', 1)
        component_product = self._create_product('Component', 'product', 1)
        self.env['mrp.bom'].create({
            'product_id': kit_product.id,
            'product_tmpl_id': kit_product.product_tmpl_id.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component_product.id, 'product_qty': 1})]
        })

        # Create the sale order with a partner that uses the inter company location
        inter_comp_location = self.env.ref('stock.stock_location_inter_company')
        partner = self.env['res.partner'].create({'name': 'Testing Partner'})
        partner.property_stock_customer = inter_comp_location
        partner.property_stock_supplier = inter_comp_location
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [
                (0, 0, {
                    'name': kit_product.name,
                    'product_id': kit_product.id,
                    'product_uom_qty': 1.0,
                })
            ]
        })
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.order_line.qty_delivered, 0)

        picking = so.picking_ids
        picking.move_ids.write({'quantity': 1, 'picked': True})
        picking.button_validate()

        self.assertEqual(so.order_line.qty_delivered, 1)

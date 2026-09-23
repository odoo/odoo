from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestSaleMrpKitBom(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("base.user_admin").write(
            {
                "email": "mitchell.admin@example.com",
            }
        )
        cls.env.user.group_ids += cls.quick_ref("product.group_product_variant")

    def _create_product(self, name, storable, price):
        return self.env["product.product"].create(
            {
                "name": name,
                "is_storable": storable,
                "standard_price": price,
            }
        )

    def test_reset_avco_kit(self):
        component_1 = self.env["product.product"].create({"name": "compo 1"})
        component_2 = self.env["product.product"].create({"name": "compo 2"})

        product_category = self.env["product.category"].create(
            {"name": "test avco kit", "property_cost_method": "average"}
        )
        attributes = self.env["product.attribute"].create({"name": "Legs"})
        steel_legs = self.env["product.attribute.value"].create(
            {"attribute_id": attributes.id, "name": "Steel"}
        )
        aluminium_legs = self.env["product.attribute.value"].create(
            {"attribute_id": attributes.id, "name": "Aluminium"}
        )

        product_template = self.env["product.template"].create(
            {
                "name": "test product",
                "categ_id": product_category.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attributes.id,
                            "value_ids": [(6, 0, [steel_legs.id, aluminium_legs.id])],
                        },
                    )
                ],
            }
        )
        product_variant_ids = product_template.product_variant_ids
        self.env["mrp.bom"].create(
            {
                "product_id": product_variant_ids[0].id,
                "product_tmpl_id": product_variant_ids[0].product_tmpl_id.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": component_1.id, "product_qty": 1})
                ],
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_id": product_variant_ids[1].id,
                "product_tmpl_id": product_variant_ids[1].product_tmpl_id.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": component_2.id, "product_qty": 1})
                ],
            }
        )
        partner = self.env["res.partner"].create({"name": "Testing Man"})
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "name": "Order line",
                "product_id": product_variant_ids[0].id,
                "order_id": so.id,
            }
        )
        so.action_confirm()
        so._action_cancel()
        so.action_draft()
        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line_ids_change:
                line_ids_change.product_id = product_variant_ids[1]

    def test_sale_mrp_kit_cost(self):
        self.customer = self.env["res.partner"].create({"name": "customer"})

        self.kit_product = self._create_product("Kit Product", True, 1.00)
        self.component_a = self._create_product("Component A", True, 1.00)
        self.component_a.product_tmpl_id.standard_price = 6
        self.component_b = self._create_product("Component B", True, 1.00)
        self.component_b.product_tmpl_id.standard_price = 10

        cat = self.env["product.category"].create(
            {"name": "fifo", "property_cost_method": "fifo"}
        )
        self.kit_product.product_tmpl_id.categ_id = cat
        self.component_a.product_tmpl_id.categ_id = cat
        self.component_b.product_tmpl_id.categ_id = cat

        self.bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.kit_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        self.env["mrp.bom.line"].create(
            {
                "product_id": self.component_a.id,
                "product_qty": 1.0,
                "bom_id": self.bom.id,
                "product_uom_id": self.env.ref("uom.product_uom_dozen").id,
            }
        )
        self.env["mrp.bom.line"].create(
            {
                "product_id": self.component_b.id,
                "product_qty": 2.0,
                "bom_id": self.bom.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_product.name,
                            "product_id": self.kit_product.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        self.assertEqual(
            so.line_ids.move_ids.mapped("description_picking"),
            ["Kit Product - 1/2", "Kit Product - 2/2"],
        )
        self.kit_product.button_bom_cost()
        self.assertEqual(
            self.kit_product.standard_price,
            92,
            "The cost of the kit must be the total cost of the components multiplied by their unit of measure",
        )

    def test_sale_mrp_kit_sale_price(self):
        if "sale_price" not in self.env["stock.move.line"]._fields:
            self.skipTest(
                "This test only runs with both sale_mrp and stock_delivery installed"
            )

        self.customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )
        self.warehouse = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse #2",
                "code": "WH02",
            }
        )

        self.kit_product = self._create_product("Kit Product", "product", 1.00)
        self.component_a = self._create_product("Component A", "product", 1.00)
        self.component_a.uom_id = self.env.ref("uom.product_uom_meter").id
        self.component_a.product_tmpl_id.list_price = 8
        self.component_b = self._create_product("Component B", "product", 1.00)
        self.component_b.product_tmpl_id.list_price = 5

        location_id = self.warehouse.lot_stock_id.id
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.component_a.id,
                    "inventory_quantity": 10,
                    "location_id": location_id,
                },
                {
                    "product_id": self.component_b.id,
                    "inventory_quantity": 24,
                    "location_id": location_id,
                },
            ]
        ).action_apply_inventory()

        self.bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.kit_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 10.0,
                            "product_uom_id": self.env.ref("uom.product_uom_meter").id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.component_b.id,
                            "product_qty": 2.0,
                            "product_uom_id": self.env.ref("uom.product_uom_dozen").id,
                        }
                    ),
                ],
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_product.name,
                            "product_id": self.kit_product.id,
                            "product_qty": 1.0,
                            "product_uom_id": self.kit_product.uom_id.id,
                        },
                    )
                ],
                "warehouse_id": self.warehouse.id,
            }
        )
        so.action_confirm()
        so.picking_ids._action_done()
        move_lines = so.picking_ids.move_ids.move_line_ids
        self.assertEqual(
            move_lines.mapped("sale_price"), [80, 120], "wrong shipping value"
        )

    def test_qty_transferred_with_bom(self):
        self.env.ref("uom.decimal_product_uom").digits = 5

        self.kit = self._create_product("Kit", True, 0.00)
        self.comp = self._create_product("Component", True, 0.00)

        bom_product_form = Form(self.env["mrp.bom"])
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = "phantom"
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.comp
            bom_line.product_qty = 0.08600
        self.bom = bom_product_form.save()

        self.customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit.name,
                            "product_id": self.kit.id,
                            "product_qty": 10.0,
                            "price_unit": 1,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.line_ids.qty_transferred, 0)

        picking = so.picking_ids
        picking.move_ids.write({"quantity": 0.86000, "picked": True})
        picking.button_validate()

        self.assertEqual(so.line_ids.qty_transferred, 10)

    def test_qty_transferred_with_bom_using_kit(self):
        self.kitA = self._create_product("Kit A", False, 0.00)
        self.kitB = self._create_product("Kit B", False, 0.00)
        self.compA = self._create_product("ComponentA", False, 0.00)
        self.compB = self._create_product("ComponentB", False, 0.00)

        bom_product_formA = Form(self.env["mrp.bom"])
        bom_product_formA.product_tmpl_id = self.kitB.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = "phantom"
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compB
            bom_line.product_qty = 1
        self.bomA = bom_product_formA.save()

        bom_product_formB = Form(self.env["mrp.bom"])
        bom_product_formB.product_tmpl_id = self.kitA.product_tmpl_id
        bom_product_formB.product_qty = 1.0
        bom_product_formB.type = "phantom"
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.compA
            bom_line.product_qty = 1
        with bom_product_formB.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.kitB
            bom_line.product_qty = 1
        self.bomB = bom_product_formB.save()

        self.customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kitA.name,
                            "product_id": self.kitA.id,
                            "product_qty": 1.0,
                            "price_unit": 1,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.line_ids.qty_transferred, 0)

        picking = so.picking_ids
        picking.button_validate()

        self.assertEqual(so.line_ids.qty_transferred, 1)

    def test_sale_kit_show_kit_in_delivery(self):
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        wh.write({"delivery_steps": "pick_ship"})

        kitA = self._create_product("Kit Product", True, 0.00)
        compA = self._create_product("ComponentA", True, 0.00)
        compB = self._create_product("ComponentB", True, 0.00)

        bom_product_formA = Form(self.env["mrp.bom"])
        bom_product_formA.product_tmpl_id = kitA.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = "phantom"
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compB
            bom_line.product_qty = 1
        bom_product_formA.save()

        customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": kitA.name,
                            "product_id": kitA.id,
                            "product_qty": 1.0,
                            "price_unit": 1,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        pick = so.picking_ids[0]
        self.assertTrue(
            pick.move_ids[0].bom_line_id,
            "All component from kits should have a bom line",
        )
        self.assertTrue(
            pick.move_ids[1].bom_line_id,
            "All component from kits should have a bom line",
        )
        pick.move_ids.write({"quantity": 1, "picked": True})
        pick.button_validate()

        ship = so.picking_ids[1]
        self.assertTrue(
            ship.move_ids[0].bom_line_id,
            "All component from kits should have a bom line",
        )
        self.assertTrue(
            ship.move_ids[1].bom_line_id,
            "All component from kits should have a bom line",
        )

    def test_qty_transferred_with_bom_using_kit2(self):
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        wh.write({"delivery_steps": "pick_ship"})

        kitAB = self._create_product("Kit AB", True, 0.00)
        kitABC = self._create_product("Kit ABC", True, 0.00)
        compA = self._create_product("ComponentA", True, 0.00)
        compB = self._create_product("ComponentB", True, 0.00)
        compC = self._create_product("ComponentC", True, 0.00)

        bom_product_formA = Form(self.env["mrp.bom"])
        bom_product_formA.product_tmpl_id = kitAB.product_tmpl_id
        bom_product_formA.product_qty = 1.0
        bom_product_formA.type = "phantom"
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compA
            bom_line.product_qty = 1
        with bom_product_formA.bom_line_ids.new() as bom_line:
            bom_line.product_id = compB
            bom_line.product_qty = 1
        bom_product_formA.save()

        bom_product_formB = Form(self.env["mrp.bom"])
        bom_product_formB.product_tmpl_id = kitABC.product_tmpl_id
        bom_product_formB.product_qty = 1.0
        bom_product_formB.type = "phantom"
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

        customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": kitAB.name,
                            "product_id": kitAB.id,
                            "product_qty": 1.0,
                            "price_unit": 1,
                            "tax_ids": False,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": kitABC.name,
                            "product_id": kitABC.id,
                            "product_qty": 1.0,
                            "price_unit": 1,
                            "tax_ids": False,
                        },
                    ),
                ],
            }
        )
        so.action_confirm()

        pick = so.picking_ids[0]
        for move in pick.move_ids:
            move.write({"quantity": 1, "picked": True})

        pick.action_put_in_pack()
        pick.button_validate()

        ship = so.picking_ids[1]

        for move_line in ship.move_line_ids:
            self.assertEqual(
                move_line.move_id.product_uom_qty,
                move_line.quantity,
                "Quantity done should be equal to the quantity reserved in the move line",
            )

    def test_kit_in_delivery_slip(self):
        kit_1, component_1, product_1, kit_3, kit_4 = self.env[
            "product.product"
        ].create(
            [
                {
                    "name": n,
                    "is_storable": True,
                }
                for n in ["Kit 1", "Compo 1", "Product 1", "Kit 3", "Kit 4"]
            ]
        )
        kit_1.description_sale = "test"

        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_1.product_tmpl_id.id,
                    "product_qty": 1,
                    "type": "phantom",
                    "bom_line_ids": [
                        (0, 0, {"product_id": component_1.id, "product_qty": 1}),
                    ],
                }
            ]
        )
        colors = ["red", "blue"]
        prod_attr = self.env["product.attribute"].create(
            {"name": "Color", "create_variant": "always"}
        )
        prod_attr_values = self.env["product.attribute.value"].create(
            [
                {"name": color, "attribute_id": prod_attr.id, "sequence": 1}
                for color in colors
            ]
        )
        kit_2 = self.env["product.template"].create(
            {
                "name": "Kit 2",
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": prod_attr.id,
                            "value_ids": [(6, 0, prod_attr_values.ids)],
                        },
                    )
                ],
            }
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_2.id,
                    "product_id": kit_2.product_variant_ids[0].id,
                    "product_qty": 1,
                    "type": "phantom",
                    "bom_line_ids": [
                        (0, 0, {"product_id": component_1.id, "product_qty": 1}),
                    ],
                }
            ]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_2.id,
                    "product_id": kit_2.product_variant_ids[1].id,
                    "product_qty": 1,
                    "type": "phantom",
                    "bom_line_ids": [
                        (0, 0, {"product_id": component_1.id, "product_qty": 1}),
                    ],
                }
            ]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_3.product_tmpl_id.id,
                    "product_qty": 1,
                    "type": "phantom",
                    "bom_line_ids": [
                        (0, 0, {"product_id": component_1.id, "product_qty": 1}),
                    ],
                }
            ]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_4.product_tmpl_id.id,
                    "product_qty": 1,
                    "type": "phantom",
                    "bom_line_ids": [
                        (0, 0, {"product_id": component_1.id, "product_qty": 1}),
                        (0, 0, {"product_id": kit_3.id, "product_qty": 1}),
                    ],
                }
            ]
        )
        customer = self.env["res.partner"].create(
            {
                "name": "customer",
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": kit_1.id,
                            "product_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_1.id,
                            "product_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": kit_2.product_variant_ids[0].id,
                            "product_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": kit_2.product_variant_ids[1].id,
                            "product_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": kit_3.id,
                            "product_qty": 1.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": kit_4.id,
                            "product_qty": 1.0,
                        },
                    ),
                ],
            }
        )
        so.action_confirm()
        picking = so.picking_ids
        self.assertEqual(len(so.picking_ids.move_ids), 7)
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking.button_validate()
        self.assertEqual(picking.state, "done")

        html_report = (
            self.env["ir.actions.report"]
            ._render_qweb_html("stock.report_deliveryslip", picking.ids)[0]
            .decode("utf-8")
            .split("\n")
        )
        keys = [
            "Kit 1",
            "Compo 1",
            "Kit 2 (red)",
            "Compo 1",
            "Kit 2 (blue)",
            "Compo 1",
            "Kit 3",
            "Compo 1",
            "Kit 4",
            "Compo 1",
            "Products not associated with a kit",
            "Product 1",
        ]
        for line in html_report:
            if not keys:
                break
            if keys[0] in line:
                keys = keys[1:]
        self.assertFalse(
            keys, "All keys should be in the report with the defined order"
        )

    def test_sale_multistep_kit_qty_change(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        warehouse.write({"delivery_steps": "pick_ship"})
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})

        kit_prod = self._create_product("kit_prod", "product", 0.00)
        sub_kit = self._create_product("sub_kit", "product", 0.00)
        component = self._create_product("component", "product", 0.00)
        component.uom_id = self.env.ref("uom.product_uom_dozen")
        self.env["stock.quant"]._update_available_quantity(
            component, warehouse.lot_stock_id, 30
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_prod.product_tmpl_id.id,
                    "product_qty": 2.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": sub_kit.id,
                                "product_qty": 5,
                            },
                        )
                    ],
                },
                {
                    "product_tmpl_id": sub_kit.product_tmpl_id.id,
                    "product_qty": 3.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": component.id,
                                "product_qty": 1,
                            },
                        )
                    ],
                },
            ]
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": kit_prod.name,
                            "product_id": kit_prod.id,
                            "product_qty": 30,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        picking_pick = so.picking_ids[0]
        picking_pick.picking_type_id.create_backorder = "never"

        self.assertEqual(picking_pick.move_ids.product_qty, 30 * 5 / 6)

        so.line_ids[0].product_qty = 60
        self.assertEqual(picking_pick.move_ids.product_qty, 60 * 5 / 6)

        picking_pick.move_ids.quantity = 25
        picking_pick.button_validate()

        picking_ship = so.picking_ids[1]
        picking_ship.picking_type_id.create_backorder = "never"
        picking_ship.move_ids.quantity = 25
        picking_ship.button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 25 / 5 * 6)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking_ship.ids,
                active_id=picking_ship.id,
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({"quantity": 10, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        return_pick.button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 15 / 5 * 6)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=return_pick.ids,
                active_id=return_pick.id,
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({"quantity": 5, "to_refund": True})
        res = return_wiz.action_create_returns()

        self.env["stock.picking"].browse(res["res_id"]).button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 20 / 5 * 6)

    def test_sale_kit_qty_change(self):

        mrp_bom_model = self.env["ir.model"]._get("mrp.bom")
        self.env["ir.access"].create(
            {
                "name": "No one allowed to access BoMs",
                "model_id": mrp_bom_model.id,
                "group_id": self.env.ref("base.group_everyone").id,
                "kind": "guard",
                "operation": "crud",
                # hides every record; a FALSE guard would deny the model instead
                "domain": "[('id', '<', 0)]",
            }
        )

        kit_product = self._create_product("Kit Product", "product", 1)
        component_a = self._create_product("Component A", "product", 1)
        self.env["mrp.bom"].create(
            {
                "product_id": kit_product.id,
                "product_tmpl_id": kit_product.product_tmpl_id.id,
                "product_qty": 1,
                "consumption": "flexible",
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": component_a.id, "product_qty": 1})
                ],
            }
        )

        partner = self.env["res.partner"].create({"name": "Testing Man"})
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        sol = self.env["sale.order.line"].create(
            {
                "name": "Order line",
                "product_id": kit_product.id,
                "order_id": so.id,
            }
        )
        so.action_confirm()

        user_admin = self.env["res.users"].search([("login", "=", "admin")])
        sol.with_user(user_admin).write({"product_qty": 5})

        self.assertEqual(sum(sol.move_ids.mapped("product_uom_qty")), 5)

    def test_sale_kit_with_mto_components_qty_change(self):
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        warehouse = self.env.ref("stock.warehouse0")
        mto_route = self.env.ref("stock.route_warehouse0_mto")
        mto_route.action_unarchive()
        manufacturing_route_id = self.ref("mrp.route_warehouse0_manufacture")
        kit_product, comp, mto_comp, subcomp = self.env["product.product"].create(
            [
                {
                    "name": "kit_product",
                    "is_storable": True,
                    "route_ids": [],
                },
                {
                    "name": "component",
                    "is_storable": True,
                    "route_ids": [],
                },
                {
                    "name": "mto_component",
                    "is_storable": True,
                    "route_ids": [Command.set([mto_route.id, manufacturing_route_id])],
                },
                {
                    "name": "subcomponent",
                    "is_storable": True,
                    "route_ids": [],
                },
            ]
        )
        self.env["stock.quant"]._update_available_quantity(
            comp, warehouse.lot_stock_id, 30.0
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_product.product_tmpl_id.id,
                    "product_qty": 2.0,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create({"product_id": comp.id, "product_qty": 5}),
                        Command.create({"product_id": mto_comp.id, "product_qty": 3}),
                    ],
                },
                {
                    "product_tmpl_id": mto_comp.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "bom_line_ids": [
                        Command.create({"product_id": subcomp.id, "product_qty": 1}),
                    ],
                },
            ]
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": kit_product.name,
                            "product_id": kit_product.id,
                            "product_qty": 4,
                        }
                    )
                ],
            }
        )
        so.action_confirm()
        self.assertRecordValues(
            so.picking_ids.move_ids.sorted("product_uom_qty"),
            [
                {"product_id": mto_comp.id, "product_uom_qty": 6.0},
                {"product_id": comp.id, "product_uom_qty": 10.0},
            ],
        )
        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line_form:
                line_form.product_qty = 10
        self.assertRecordValues(
            so.picking_ids.move_ids.sorted("product_uom_qty"),
            [
                {"product_id": mto_comp.id, "product_uom_qty": 6.0},
                {"product_id": mto_comp.id, "product_uom_qty": 9.0},
                {"product_id": comp.id, "product_uom_qty": 25.0},
            ],
        )

    def test_inter_company_qty_transferred_with_kit(self):
        self.env.user.write(
            {"group_ids": [(4, self.env.ref("base.group_multi_company").id)]}
        )
        kit_product = self._create_product("Kit", "product", 1)
        component_product = self._create_product("Component", "product", 1)
        self.env["mrp.bom"].create(
            {
                "product_id": kit_product.id,
                "product_tmpl_id": kit_product.product_tmpl_id.id,
                "product_qty": 1,
                "consumption": "flexible",
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": component_product.id, "product_qty": 1})
                ],
            }
        )

        inter_comp_location = self.env.ref("stock.stock_location_inter_company")
        partner = self.env["res.partner"].create({"name": "Testing Partner"})
        partner.property_stock_customer = inter_comp_location
        partner.property_stock_supplier = inter_comp_location
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": kit_product.name,
                            "product_id": kit_product.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        self.assertTrue(so.picking_ids)
        self.assertEqual(so.line_ids.qty_transferred, 0)

        picking = so.picking_ids
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking.button_validate()

        self.assertEqual(so.line_ids.qty_transferred, 1)

    def _confirm_kit_sale(self, kit_uom, component_uom, kit_qty=3.0, comp_per_kit=2.0):
        kit = self.env["product.product"].create(
            {
                "name": "Kit",
                "is_storable": True,
                "uom_id": kit_uom.id,
            }
        )
        component = self.env["product.product"].create(
            {
                "name": "Component",
                "is_storable": True,
                "uom_id": component_uom.id,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_qty": comp_per_kit,
                            "product_uom_id": component_uom.id,
                        }
                    )
                ],
            }
        )
        partner = self.env["res.partner"].create({"name": "Kit customer"})
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": kit.id,
                            "product_qty": kit_qty,
                        }
                    )
                ],
            }
        )
        so.action_confirm()
        move = so.line_ids.move_ids
        self.assertEqual(move.product_id, component)
        return move

    def test_kit_component_packaging_uom_falls_back_cross_category(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_kg = self.env.ref("uom.product_uom_kgm")
        self.assertFalse(uom_kg._has_common_reference(uom_unit))

        move = self._confirm_kit_sale(uom_unit, uom_kg)

        self.assertEqual(
            move.sale_line_id.product_uom_id,
            uom_unit,
            "the kit sale line is legitimately measured in Units",
        )
        self.assertEqual(move.packaging_uom_id, uom_kg)
        self.assertEqual(move.quantity_packaging_uom, move.product_uom_qty)
        self.assertEqual(move.quantity_packaging_uom, 6.0)

    def test_kit_component_packaging_uom_inherited_when_compatible(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        self.assertTrue(uom_dozen._has_common_reference(uom_unit))

        move = self._confirm_kit_sale(uom_unit, uom_dozen)

        self.assertEqual(move.packaging_uom_id, uom_unit)
        self.assertEqual(move.sale_line_id.product_uom_id, uom_unit)

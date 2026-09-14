from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPurchaseMrpFlow(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.UoM = cls.env["uom.uom"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)]
        )
        cls.stock_location = cls.warehouse.lot_stock_id

        grp_uom = cls.env.ref("uom.group_uom")
        group_user = cls.env.ref("base.group_user")
        group_user.write({"implied_ids": [(4, grp_uom.id)]})
        cls.env.user.write({"group_ids": [(4, grp_uom.id)]})

        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_gm = cls.env.ref("uom.product_uom_gram")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")

        cls.component_a = cls._create_product_with_form("Comp A", cls.uom_unit)
        cls.component_b = cls._create_product_with_form("Comp B", cls.uom_unit)
        cls.component_c = cls._create_product_with_form("Comp C", cls.uom_unit)
        cls.component_d = cls._create_product_with_form("Comp D", cls.uom_unit)
        cls.component_e = cls._create_product_with_form("Comp E", cls.uom_unit)
        cls.component_f = cls._create_product_with_form("Comp F", cls.uom_unit)
        cls.component_g = cls._create_product_with_form("Comp G", cls.uom_unit)

        cls.kit_1 = cls._create_product_with_form("Kit 1", cls.uom_unit)

        cls.bom_kit_1 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_1.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine = cls.env["mrp.bom.line"]
        BomLine.create(
            {
                "product_id": cls.component_a.id,
                "product_qty": 2.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_b.id,
                "product_qty": 1.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_c.id,
                "product_qty": 3.0,
                "bom_id": cls.bom_kit_1.id,
            }
        )

        cls.kit_2 = cls._create_product_with_form("Kit 2", cls.uom_unit)
        cls.kit_3 = cls._create_product_with_form("kit 3", cls.uom_unit)
        cls.kit_parent = cls._create_product_with_form("Kit Parent", cls.uom_unit)

        bom_kit_2 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_2.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_d.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_2.id,
            }
        )
        BomLine.create(
            {"product_id": cls.kit_1.id, "product_qty": 2.0, "bom_id": bom_kit_2.id}
        )

        bom_kit_parent = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_parent.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_e.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_parent.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.kit_2.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_parent.id,
            }
        )

        bom_kit_3 = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_3.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )

        BomLine.create(
            {
                "product_id": cls.component_f.id,
                "product_qty": 1.0,
                "bom_id": bom_kit_3.id,
            }
        )
        BomLine.create(
            {
                "product_id": cls.component_g.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_3.id,
            }
        )

        BomLine.create(
            {
                "product_id": cls.kit_3.id,
                "product_qty": 2.0,
                "bom_id": bom_kit_parent.id,
            }
        )

    @classmethod
    def _create_product_with_form(cls, name, uom_id, routes=()):
        return cls.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "categ_id": cls.env.ref("product.product_category_goods").id,
                "uom_id": uom_id.id,
                "route_ids": [Command.set([route.id for route in routes])],
            }
        )

    def _process_quantities(self, moves, quantities_to_process):
        moves_to_process = moves.filtered(
            lambda m: m.product_id in quantities_to_process
        )
        for move in moves_to_process:
            move.quantity = quantities_to_process[move.product_id]
            move.picked = True

    def _assert_quantities(self, moves, quantities_to_process):
        moves_to_process = moves.filtered(
            lambda m: m.product_id in quantities_to_process
        )
        for move in moves_to_process:
            self.assertEqual(
                move.product_uom_qty, quantities_to_process[move.product_id]
            )

    def _create_move_quantities(self, qty_to_process, components, warehouse):
        for comp in components:
            f = Form(self.env["stock.move"])
            f.name = "Test Receipt Components"
            f.location_id = self.env.ref("stock.stock_location_suppliers")
            f.location_dest_id = warehouse.lot_stock_id
            f.product_id = comp
            f.product_uom_id = qty_to_process[comp][1]
            f.product_uom_qty = qty_to_process[comp][0]
            move = f.save()
            move._action_confirm()
            move._action_assign()
            move_line = move.move_line_ids[0]
            move_line.quantity = qty_to_process[comp][0]
            move._action_done()

    def test_kit_component_cost(self):
        self.kit_1.categ_id.property_cost_method = "fifo"
        self.kit_1.categ_id.property_valuation = "real_time"

        self.kit_1.bom_ids.product_qty = 3

        po = Form(self.env["purchase.order"])
        po.partner_id = self.env["res.partner"].create({"name": "Testy"})
        with po.line_ids.new() as line:
            line.product_id = self.kit_1
            line.product_qty = 120
            line.price_unit = 1260
        po = po.save()
        po.action_confirm()
        po.picking_ids.button_validate()

        components = [
            self.component_a,
            self.component_b,
            self.component_c,
        ]

        self.assertAlmostEqual(
            sum(k.standard_price * k.qty_available for k in components),
            120 * 1260,
            delta=0.5,
        )

    def test_kit_component_cost_multi_currency(self):
        kit = self._create_product_with_form("Kit", self.uom_unit)
        cmp = self._create_product_with_form("CMP", self.uom_unit)

        bom_kit = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        self.env["mrp.bom.line"].create(
            {"product_id": cmp.id, "product_qty": 3.0, "bom_id": bom_kit.id}
        )

        kit.categ_id.property_cost_method = "fifo"
        kit.categ_id.property_valuation = "real_time"

        mock_currency = self.env["res.currency"].create(
            {
                "name": "MOCK",
                "symbol": "MC",
            }
        )
        self.env["res.currency.rate"].create(
            {
                "name": "2023-01-01",
                "company_rate": 100.0,
                "currency_id": mock_currency.id,
                "company_id": self.env.company.id,
            }
        )

        po = Form(self.env["purchase.order"])
        po.partner_id = self.env["res.partner"].create({"name": "Testy"})
        po.currency_id = mock_currency

        with po.line_ids.new() as line:
            line.product_id = kit
            line.product_qty = 1
            line.price_unit = 300.00

        po = po.save()
        po.action_confirm()
        po.picking_ids.button_validate()

        move = po.picking_ids.move_ids
        self.assertEqual(move.value / move.quantity, 1)

    def test_01_sale_mrp_kit_qty_delivered(self):

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["purchase.order"])
        f.partner_id = partner
        with f.line_ids.new() as line:
            line.product_id = self.kit_parent
            line.product_qty = 7.0
            line.price_unit = 10

        po = f.save()
        po.action_confirm()

        self.assertEqual(len(po.picking_ids), 1)
        order_line = po.line_ids[0]
        picking_original = po.picking_ids[0]
        move_ids = picking_original.move_ids
        products = move_ids.mapped("product_id")
        kits = [self.kit_parent, self.kit_3, self.kit_2, self.kit_1]
        components = [
            self.component_a,
            self.component_b,
            self.component_c,
            self.component_d,
            self.component_e,
            self.component_f,
            self.component_g,
        ]
        expected_quantities = {
            self.component_a: 56.0,
            self.component_b: 28.0,
            self.component_c: 84.0,
            self.component_d: 14.0,
            self.component_e: 7.0,
            self.component_f: 14.0,
            self.component_g: 28.0,
        }

        self.assertEqual(len(move_ids), 7)
        self.assertTrue(not any(kit in products for kit in kits))
        self.assertTrue(all(component in products for component in components))
        self._assert_quantities(move_ids, expected_quantities)

        qty_to_process = 7
        move_ids.write({"quantity": qty_to_process, "picked": True})

        pick = po.picking_ids[0]
        Form.from_action(self.env, pick.button_validate()).save().process()

        self.assertEqual(len(po.picking_ids), 2)
        backorder_1 = po.picking_ids - picking_original
        self.assertEqual(backorder_1.backorder_id.id, picking_original.id)

        self.assertEqual(order_line.qty_transferred, 0)

        qty_to_process = {
            self.component_a: 1,
            self.component_c: 5,
        }
        self._process_quantities(backorder_1.move_ids, qty_to_process)

        Form.from_action(self.env, backorder_1.button_validate()).save().process()

        self.assertEqual(order_line.qty_transferred, 1)

        self.assertEqual(len(po.picking_ids), 3)
        backorder_2 = po.picking_ids - picking_original - backorder_1
        self.assertEqual(backorder_2.backorder_id.id, backorder_1.id)

        expected_quantities = {
            self.component_a: 48,
            self.component_b: 21,
            self.component_c: 72,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 21,
        }

        self.assertEqual(len(backorder_2.move_ids), 6)
        move_comp_e = backorder_2.move_ids.filtered(
            lambda m: m.product_id.id == self.component_e.id
        )
        self.assertFalse(move_comp_e)
        self._assert_quantities(backorder_2.move_ids, expected_quantities)

        qty_to_process = {
            self.component_a: 16,
            self.component_b: 5,
            self.component_c: 24,
            self.component_g: 5,
        }
        self._process_quantities(backorder_2.move_ids, qty_to_process)

        Form.from_action(self.env, backorder_2.button_validate()).save().process()

        self.assertEqual(order_line.qty_transferred, 3)

        self.assertEqual(len(po.picking_ids), 4)
        backorder_3 = po.picking_ids - (picking_original + backorder_1 + backorder_2)
        self.assertEqual(backorder_3.backorder_id.id, backorder_2.id)

        expected_quantities = {
            self.component_a: 32,
            self.component_b: 16,
            self.component_c: 48,
            self.component_d: 7,
            self.component_f: 7,
            self.component_g: 16,
        }
        self._assert_quantities(backorder_3.move_ids, expected_quantities)

        self._process_quantities(backorder_3.move_ids, expected_quantities)

        backorder_3.button_validate()
        self.assertEqual(order_line.qty_transferred, 7.0)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=backorder_3.ids,
                active_id=backorder_3.ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write(
                {
                    "quantity": expected_quantities[return_move.product_id],
                    "to_refund": True,
                }
            )
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        return_pick.button_validate()

        self.assertEqual(order_line.qty_transferred, 3)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=return_pick.ids,
                active_id=return_pick.ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for move in return_wiz.product_return_moves:
            move.quantity = expected_quantities[move.product_id]
        res = return_wiz.action_create_returns()
        return_of_return_pick = self.env["stock.picking"].browse(res["res_id"])

        for move in return_of_return_pick.move_ids:
            move.write(
                {
                    "quantity": expected_quantities[move.product_id] - 1,
                    "to_refund": True,
                }
            )

        Form.from_action(
            self.env, return_of_return_pick.button_validate()
        ).save().process()

        self.assertEqual(order_line.qty_transferred, 6)

        self.assertEqual(len(po.picking_ids), 7)
        backorder_4 = po.picking_ids - (
            picking_original
            + backorder_1
            + backorder_2
            + backorder_3
            + return_of_return_pick
            + return_pick
        )
        self.assertEqual(backorder_4.backorder_id.id, return_of_return_pick.id)

        for move in backorder_4.move_ids:
            self.assertEqual(move.product_qty, 1)

    def test_concurent_procurements(self):
        warehouse = self.warehouse
        buy_route = warehouse.buy_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id

        vendor1 = self.env["res.partner"].create(
            {"name": "aaa", "email": "from.test@example.com"}
        )

        component = self.env["product.product"].create(
            {
                "name": "component",
                "is_storable": True,
                "route_ids": [(4, buy_route.id)],
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "product_id": component.id,
                "partner_id": vendor1.id,
                "price": 50,
            }
        )
        finished = self.env["product.product"].create(
            {
                "name": "finished",
                "is_storable": True,
                "route_ids": [(4, manufacture_route.id)],
            }
        )
        self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "A RR",
                "location_id": warehouse.lot_stock_id.id,
                "product_id": component.id,
                "route_id": buy_route.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )
        self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "A RR",
                "location_id": warehouse.lot_stock_id.id,
                "product_id": finished.id,
                "route_id": manufacture_route.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": finished.id,
                "product_tmpl_id": finished.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "operation_ids": [],
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": component.id, "product_qty": 1}),
                ],
            }
        )

        picking_form = Form(self.env["stock.picking"])
        picking_form.picking_type_id = warehouse.out_type_id
        with picking_form.move_ids.new() as move:
            move.product_id = finished
            move.product_uom_qty = 3
        with picking_form.move_ids.new() as move:
            move.product_id = component
            move.product_uom_qty = 2
        picking = picking_form.save()
        picking.action_confirm()

        purchase = (
            self.env["purchase.order.line"]
            .search(
                [
                    ("product_id", "=", component.id),
                ]
            )
            .order_id
        )
        self.assertTrue(purchase)
        self.assertEqual(len(purchase), 2)
        self.assertEqual(sum(purchase.line_ids.mapped("product_qty")), 5)

    def test_01_purchase_mrp_kit_qty_change(self):
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})

        self.po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_1.name,
                            "product_id": self.kit_1.id,
                            "product_qty": 1,
                            "product_uom_id": self.kit_1.uom_id.id,
                            "price_unit": 60.0,
                            "date_commitment": fields.Datetime.now(),
                        },
                    )
                ],
            }
        )
        self.po.action_confirm()

        self.assertEqual(
            self.po.picking_ids.move_ids[0].product_uom_qty,
            2,
            "The quantity of components must be created according to the BOM",
        )
        self.assertEqual(
            self.po.picking_ids.move_ids[1].product_uom_qty,
            1,
            "The quantity of components must be created according to the BOM",
        )
        self.assertEqual(
            self.po.picking_ids.move_ids[2].product_uom_qty,
            3,
            "The quantity of components must be created according to the BOM",
        )

        self.po.line_ids[0].product_qty = 2
        self.assertEqual(
            self.po.picking_ids.move_ids[0].product_uom_qty,
            4,
            "The amount of the kit components must be updated when changing the quantity of the kit.",
        )
        self.assertEqual(
            self.po.picking_ids.move_ids[1].product_uom_qty,
            2,
            "The amount of the kit components must be updated when changing the quantity of the kit.",
        )
        self.assertEqual(
            self.po.picking_ids.move_ids[2].product_uom_qty,
            6,
            "The amount of the kit components must be updated when changing the quantity of the kit.",
        )

    def test_procurement_with_preferred_route(self):
        self.warehouse.reception_steps = "three_steps"

        manu_route = self.warehouse.manufacture_pull_id.route_id
        buy_route = self.warehouse.buy_pull_id.route_id

        self.env["stock.rule"].sudo().search([]).sequence = 1
        buy_route.sudo().rule_ids.sequence = 2

        vendor = self.env["res.partner"].create({"name": "super vendor"})

        product = self.env["product.product"].create(
            {
                "name": "super product",
                "is_storable": True,
                "seller_ids": [(0, 0, {"partner_id": vendor.id})],
                "route_ids": [(4, manu_route.id), (4, buy_route.id)],
            }
        )

        rr = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": product.name,
                "location_id": self.warehouse.lot_stock_id.id,
                "product_id": product.id,
                "product_min_qty": 1,
                "product_max_qty": 1,
                "route_id": buy_route.id,
            }
        )
        rr.action_replenish()

        po = self.env["purchase.order"].search([("partner_id", "=", vendor.id)])
        self.assertTrue(po)

        po.action_confirm()

    def test_procurement_with_preferred_route_2(self):
        manu_route = self.warehouse.manufacture_pull_id.route_id
        buy_route = self.warehouse.buy_pull_id.route_id

        vendor = self.env["res.partner"].create({"name": "super vendor"})

        product = self.env["product.product"].create(
            {
                "name": "super product",
                "is_storable": True,
                "seller_ids": [(0, 0, {"partner_id": vendor.id})],
                "route_ids": buy_route,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1.0,
                "product_uom_id": product.uom_id.id,
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        picking = self.env["stock.picking"].create(
            {
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "picking_type_id": warehouse.out_type_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "product_uom_qty": 1,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        picking.action_assign()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertEqual(
            orderpoint_product.effective_route_id,
            buy_route,
            "The buy route set on the product should win over the BoM it also has",
        )
        orderpoint_product.unlink()
        product.write({"route_ids": [(3, buy_route.id), (4, manu_route.id)]})
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertEqual(
            orderpoint_product.effective_route_id,
            manu_route,
            "The route manufacture should be set on the orderpoint",
        )

    def test_compute_bom_days_00(self):
        purchase_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        manufacture_route = self.env["stock.route"].search(
            [("name", "=", "Manufacture")]
        )
        vendor = self.env["res.partner"].create({"name": "super vendor"})

        company_1 = self.kit_parent.bom_ids.company_id
        company_2 = self.env["res.company"].create(
            {
                "name": "TestCompany2",
            }
        )

        company_1.days_to_purchase = 0
        company_2.days_to_purchase = 0

        components = (
            self.component_a
            | self.component_b
            | self.component_c
            | self.component_d
            | self.component_e
            | self.component_f
            | self.component_g
        )
        kits = self.kit_parent | self.kit_1 | self.kit_2 | self.kit_3
        kits.route_ids = [(6, 0, manufacture_route.ids)]
        components.write(
            {
                "route_ids": [(6, 0, purchase_route.ids)],
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": vendor.id,
                            "min_qty": 1,
                            "price": 1,
                            "delay": 1,
                        },
                    )
                ],
            }
        )

        bom_kit_parent = self.kit_parent.bom_ids
        bom_kit_parent.action_compute_bom_days()
        self.assertEqual(bom_kit_parent.days_to_prepare_mo, 1)

        company_1.days_to_purchase = 10
        company_2.days_to_purchase = 20

        bom_kit_parent.action_compute_bom_days()
        self.assertEqual(bom_kit_parent.days_to_prepare_mo, 10 + 1)

        self.kit_1.bom_ids.company_id = company_2
        bom_kit_parent.action_compute_bom_days()
        self.assertEqual(bom_kit_parent.days_to_prepare_mo, 20 + 1)

        kits.bom_ids.company_id = False
        bom_kit_parent.action_compute_bom_days()
        self.assertEqual(bom_kit_parent.days_to_prepare_mo, 1)

    def test_orderpoint_with_manufacture_security_lead_time(self):
        self.env.company.horizon_days = 0

        product = self.env["product.product"].create(
            {
                "name": "super product",
                "is_storable": True,
                "route_ids": [
                    (4, self.env.ref("mrp.route_warehouse0_manufacture").id),
                    (4, self.env.ref("purchase_stock.route_warehouse0_buy").id),
                ],
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.env["res.partner"]
                            .create({"name": "super vendor"})
                            .id,
                            "min_qty": 1,
                            "price": 1,
                        },
                    )
                ],
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "produce_delay": 1,
                "product_qty": 1,
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "qty_to_order": 5,
                "warehouse_id": self.warehouse.id,
                "route_id": self.env.ref("mrp.route_warehouse0_manufacture").id,
            }
        )
        self.assertEqual(
            orderpoint.lead_horizon_date, (fields.Date.today() + timedelta(days=1))
        )
        orderpoint.action_replenish()
        mo = self.env["mrp.production"].search([("product_id", "=", product.id)])
        self.assertEqual(mo.product_uom_qty, 5)
        self.assertEqual(mo.date_start.date(), fields.Date.today())

    def test_mo_overview(self):
        component = self.env["product.product"].create(
            {
                "name": "component",
                "is_storable": True,
                "standard_price": 80,
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.env["res.partner"]
                            .create({"name": "super vendor"})
                            .id,
                            "min_qty": 3,
                            "price": 10,
                        },
                    )
                ],
            }
        )
        finished_product = self.env["product.product"].create(
            {
                "name": "finished_product",
                "is_storable": True,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": component.id,
                            "product_qty": 2,
                            "product_uom_id": component.uom_id.id,
                        },
                    )
                ],
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": finished_product.id,
                "product_qty": 1,
                "product_uom_id": finished_product.uom_id.id,
            }
        )
        self.env.flush_all()
        report_values = self.env["report.mrp.report_mo_overview"]._get_report_data(
            mo.id
        )["components"][0]["summary"]
        self.assertEqual(report_values["name"], component.name)
        self.assertEqual(report_values["quantity"], 2)
        self.assertEqual(report_values["mo_cost"], 160)
        mo_2 = self.env["mrp.production"].create(
            {
                "product_id": finished_product.id,
                "product_qty": 2,
                "product_uom_id": finished_product.uom_id.id,
            }
        )
        self.env.flush_all()
        report_values = self.env["report.mrp.report_mo_overview"]._get_report_data(
            mo_2.id
        )["components"][0]["summary"]
        self.assertEqual(report_values["quantity"], 4)
        self.assertEqual(report_values["mo_cost"], 40)

    def test_bom_report_incoming_po(self):
        location = self.stock_location
        uom_unit = self.env.ref("uom.product_uom_unit")
        final_product_tmpl = self.env["product.template"].create(
            {"name": "Final Product", "is_storable": True}
        )
        component_product = self.env["product.product"].create(
            {"name": "Compo 1", "is_storable": True}
        )

        self.env["stock.quant"]._update_available_quantity(
            component_product, location, 3.0
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final_product_tmpl.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 4,
                            "product_uom_id": uom_unit.id,
                        }
                    ),
                ],
            }
        )

        def create_order(product_id, partner_id, date_order):
            f = Form(self.env["purchase.order"])
            f.partner_id = partner_id
            f.date_order = date_order
            with f.line_ids.new() as line:
                line.product_id = product_id
                line.product_qty = 3.0
                line.price_unit = 10
            return f.save()

        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        po_today = create_order(component_product, partner, fields.Datetime.now())
        po_5days = create_order(
            component_product, partner, fields.Datetime.now() + timedelta(days=5)
        )

        po_today.action_confirm()
        po_5days.action_confirm()
        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )
        line_values = report_values["lines"]["components"][0]
        self.assertEqual(
            line_values["availability_state"],
            "estimated",
            "The merged components should be estimated.",
        )

    def test_bom_report_incoming_po2(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        final_product_tmpl = self.env["product.template"].create(
            {"name": "Final Product", "is_storable": True}
        )
        component_product = self.env["product.product"].create(
            {"name": "Compo 1", "is_storable": True}
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final_product_tmpl.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": uom_unit.id,
                        }
                    ),
                ],
            }
        )
        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        f = Form(self.env["purchase.order"])
        f.partner_id = partner
        f.date_order = fields.Datetime.now()
        with f.line_ids.new() as line:
            line.product_id = component_product
            line.product_qty = 6.0
            line.price_unit = 10
        po_today = f.save()
        po_today.action_confirm()
        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )
        line_values = report_values["lines"]["components"][0]
        self.assertEqual(
            line_values["availability_state"],
            "expected",
            "The first component should be expected as there is an incoming PO.",
        )

    def test_purchase_multistep_kit_qty_change(self):
        self.warehouse.write({"reception_steps": "two_steps"})
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})

        kit_prod = self._create_product_with_form("kit_prod", self.uom_unit)
        sub_kit = self._create_product_with_form("sub_kit", self.uom_unit)
        component = self._create_product_with_form("component", self.uom_unit)

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

        po = self.env["purchase.order"].create(
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
        po.action_confirm()
        picking = po.picking_ids
        self.assertEqual(picking.move_line_ids.quantity_product_uom, 30 * 5 / 6)

        po.line_ids[0].product_qty = 60
        self.assertEqual(picking.move_line_ids.quantity_product_uom, 60 * 5 / 6)

        picking.move_line_ids.quantity = 25
        picking.with_context(skip_backorder=True).button_validate()
        self.assertEqual(po.line_ids.qty_transferred, 25 / 5 * 6)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({"quantity": 10, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        return_pick.button_validate()
        self.assertEqual(po.line_ids.qty_transferred, 15 / 5 * 6)

    def test_bom_report_vendor_quantities(self):
        buy_route = self.warehouse.buy_pull_id.route_id
        final = self.env["product.product"].create(
            {"name": "Final", "type": "consu", "is_storable": True}
        )
        self.component_a.write(
            {
                "route_ids": [Command.link(buy_route.id)],
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner_a.id, "min_qty": 0, "delay": 5}
                    ),
                    Command.create(
                        {"partner_id": self.partner_b.id, "min_qty": 5, "delay": 1}
                    ),
                ],
            }
        )
        self.component_b.write(
            {
                "route_ids": [Command.link(buy_route.id)],
                "seller_ids": [
                    Command.create({"partner_id": self.partner_a.id, "min_qty": 5}),
                ],
            }
        )
        self.component_c.write(
            {
                "route_ids": [Command.link(buy_route.id)],
                "seller_ids": [
                    Command.create({"partner_id": self.partner_a.id, "min_qty": 5}),
                ],
            }
        )
        self.component_d.write(
            {
                "route_ids": [Command.link(buy_route.id)],
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner_a.id, "min_qty": 12, "price": 10}
                    ),
                ],
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 10,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.component_b.id,
                            "product_qty": 3,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.component_c.id,
                            "product_qty": 1,
                            "product_uom_id": self.uom_dozen.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.component_d.id,
                            "product_qty": 3,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )

        compo_a_values = report_values["lines"]["components"][0]
        self.assertEqual(
            compo_a_values["route_detail"],
            self.partner_b.display_name,
            "Compo A should have picked the fastest supplier",
        )
        compo_b_values = report_values["lines"]["components"][1]
        self.assertEqual(
            compo_b_values["route_detail"],
            self.partner_a.display_name,
            "Compo B should have found the supplier, even without enough qty",
        )
        self.assertTrue(
            compo_b_values["route_alert"],
            "Should be true as there isn't enough quantity for this vendor",
        )
        compo_c_values = report_values["lines"]["components"][2]
        self.assertEqual(compo_c_values["route_detail"], self.partner_a.display_name)
        self.assertFalse(
            compo_c_values["route_alert"],
            "Should be false as 1 dozen > 5 units for this vendor",
        )
        compo_d_values = report_values["lines"]["components"][3]
        self.assertEqual(
            compo_d_values["route_detail"],
            self.partner_a.display_name,
            "Compo D should have found the supplier, even without enough qty",
        )
        self.assertTrue(
            compo_d_values["route_alert"],
            "Should be true as 3 units < 1 dozen for this vendor",
        )

    def test_valuation_with_backorder(self):
        fifo_category = self.env["product.category"].create(
            {
                "name": "FIFO",
                "property_cost_method": "fifo",
                "property_valuation": "real_time",
            }
        )
        kit, cmp1, cmp2 = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "standard_price": 0,
                    "is_storable": True,
                    "categ_id": fifo_category.id,
                }
                for name in ["Kit", "Cmp1", "Cmp2"]
            ]
        )
        kit.uom_id = self.uom_gm.id
        cmp1.uom_id = self.uom_gm.id
        cmp2.uom_id = self.uom_kg.id

        self.env["mrp.bom"].create(
            {
                "product_uom_id": self.uom_kg.id,
                "product_qty": 3,
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cmp1.id,
                            "product_qty": 2,
                            "product_uom_id": self.uom_kg.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": cmp2.id,
                            "product_qty": 1,
                            "product_uom_id": self.uom_gm.id,
                        },
                    ),
                ],
            }
        )

        po_form = Form(self.env["purchase.order"])
        partner = self.env["res.partner"].create({"name": "My Test Partner"})
        po_form.partner_id = partner
        with po_form.line_ids.new() as pol_form:
            pol_form.product_id = kit
            pol_form.product_qty = 30
            pol_form.product_uom_id = self.uom_kg
            pol_form.price_unit = 90000
            pol_form.tax_ids.clear()
        po = po_form.save()
        po.action_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids[0].quantity = 4
        receipt.move_line_ids[1].quantity = 2
        Form.from_action(self.env, receipt.button_validate()).save().process()
        received = po.picking_ids.filtered(lambda p: p.state == "done")
        backorder = po.picking_ids - received
        self.assertRecordValues(
            received.move_ids.filtered("is_valued").sorted("product_id"),
            [
                {"product_id": cmp1.id, "quantity": 4.0, "product_uom_qty": 4.0},
                {"product_id": cmp2.id, "quantity": 2.0, "product_uom_qty": 2.0},
            ],
        )
        self.assertRecordValues(
            backorder.move_ids.sorted("product_id"),
            [
                {"product_id": cmp1.id, "product_uom_qty": 16.0},
                {"product_id": cmp2.id, "product_uom_qty": 8.0},
            ],
        )
        received_share = 4.0 / 20.0
        for move in received.move_ids:
            self.assertAlmostEqual(
                move.value,
                po.line_ids.price_subtotal * received_share * 0.5,
                places=2,
                msg=move.product_id.name,
            )
        self.assertAlmostEqual(
            sum(received.move_ids.mapped("value")),
            po.line_ids.price_subtotal * received_share,
            places=2,
        )

        backorder.button_validate()
        self.assertAlmostEqual(
            sum(po.picking_ids.move_ids.filtered("is_valued").mapped("value")),
            po.line_ids.price_subtotal,
            places=2,
        )

    def test_mo_overview_mto_purchase_with_backorders(self):
        self.warehouse.reception_steps = "two_steps"
        self.env.ref("stock.route_warehouse0_mto").active = True
        route_buy = self.warehouse.buy_pull_id.route_id
        route_mto = self.warehouse.mto_pull_id.route_id
        route_mto.rule_ids.procure_method = "make_to_order"
        self.component_a.write(
            {
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner_a.id},
                    )
                ],
                "route_ids": [
                    Command.link(route_buy.id),
                    Command.link(route_mto.id),
                ],
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.component_b.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 2.0,
                        }
                    ),
                ],
            }
        )
        with Form(self.env["mrp.production"]) as prod_form:
            prod_form.product_id = self.component_b
            prod_form.bom_id = bom
            prod_form.product_qty = 3
            production = prod_form.save()
        production.action_confirm()
        self.assertEqual(production.purchase_order_count, 1)
        purchase = production.reference_ids.purchase_ids
        self.assertEqual(len(purchase), 1)

        with Form(production) as prod_form:
            prod_form.qty_producing = 1
            production = prod_form.save()
        backorder_action = production.button_mark_done()
        backorder_wizard = Form(
            self.env["mrp.production.backorder"].with_context(
                **backorder_action["context"]
            )
        )
        backorder_wizard.save().action_backorder()

        backorder = production.production_group_id.production_ids - production
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.product_qty, 2)
        report_values = self.env["report.mrp.report_mo_overview"]._get_report_data(
            backorder.id
        )
        self.assertEqual(report_values["summary"]["quantity"], backorder.product_qty)
        self.assertEqual(report_values["components"][0]["summary"]["quantity"], 4)
        replenishments = report_values["components"][0]["replenishments"]
        self.assertEqual(len(replenishments), 1)
        self.assertEqual(replenishments[0]["summary"]["name"], purchase.name)

    def test_cancel_mo_with_mto_purchase_component(self):
        self.env.ref("stock.route_warehouse0_mto").active = True
        route_buy = self.warehouse.buy_pull_id.route_id
        route_mto = self.warehouse.mto_pull_id.route_id
        route_mto.rule_ids.procure_method = "make_to_order"
        self.component_a.write(
            {
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner_a.id},
                    )
                ],
                "route_ids": [
                    Command.link(route_buy.id),
                    Command.link(route_mto.id),
                ],
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.component_b.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_qty": 2.0,
                        }
                    ),
                ],
            }
        )
        with Form(self.env["mrp.production"]) as prod_form:
            prod_form.product_id = self.component_b
            prod_form.bom_id = bom
            prod_form.product_qty = 3
            production = prod_form.save()
        production.action_confirm()
        self.assertEqual(production.purchase_order_count, 1)
        purchase = production.reference_ids.purchase_ids
        self.assertEqual(len(purchase), 1)
        self.assertFalse(purchase.activity_ids)
        production.action_cancel()
        self.assertEqual(production.state, "cancel")
        self.assertEqual(len(purchase.activity_ids), 1)

    def test_total_cost_share_rounded_to_precision(self):
        kit, compo01, compo02 = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "standard_price": price,
                }
                for name, price in [("Kit", 30), ("Compo 01", 10), ("Compo 02", 20)]
            ]
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": compo01.id,
                            "product_qty": 1,
                            "cost_share": 99.99,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": compo02.id,
                            "product_qty": 1,
                            "cost_share": 0.01,
                        },
                    ),
                ],
            }
        )
        self.assertTrue(bom)

    def test_kit_price_without_rounding(self):
        warehouse = self.warehouse
        buy_route = warehouse.buy_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id

        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )

        prod, compo = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "type": "consu",
                    "categ_id": avco_category.id,
                    "route_ids": [(4, route_id)],
                }
                for name, route_id in [
                    ("product a", manufacture_route.id),
                    ("component a", buy_route.id),
                ]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": prod.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": compo.id,
                            "product_qty": 12,
                        },
                    )
                ],
            }
        )

        po_form = Form(self.env["purchase.order"])
        partner = self.env["res.partner"].create({"name": "Testy"})
        po_form.partner_id = partner
        with po_form.line_ids.new() as pol_form:
            pol_form.product_id = prod
            pol_form.product_qty = 1
            pol_form.price_unit = 100
            pol_form.tax_ids.clear()
        po = po_form.save()
        po.action_confirm()
        receipt = po.picking_ids
        receipt.button_validate()
        move = receipt.move_ids[0]
        self.assertEqual(move.value, 100)

    def test_valuation_by_lot_component_in_kit(self):
        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        self.component_a.categ_id = avco_category
        self.component_a.is_storable = True
        self.component_a.lot_valuated = True
        lot_a = self.env["stock.lot"].create(
            {
                "name": "lot_a",
                "product_id": self.component_a.id,
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.kit_1.id,
                            "product_uom_id": self.kit_1.uom_id.id,
                            "price_unit": 60.0,
                            "product_qty": 2,
                        }
                    )
                ],
            }
        )
        po.action_confirm()
        self.assertEqual(po.state, "done")
        self.assertEqual(self.component_a.standard_price, 0)
        picking = po.picking_ids
        move_line = picking.move_line_ids.filtered(
            lambda m: m.product_id == self.component_a
        )
        move_line.lot_id = lot_a
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertAlmostEqual(self.component_a.standard_price, 10.0)
        self.assertAlmostEqual(lot_a.standard_price, 10.0)
        self.assertEqual(lot_a.product_qty, 4)
        self.assertEqual(lot_a.total_value, 40)

    def test_inter_company_received_qty_with_kit(self):
        inter_comp_location = self.env.ref("stock.stock_location_inter_company")
        partner = self.env["res.partner"].create({"name": "Testing Partner"})
        partner.property_stock_customer = inter_comp_location
        partner.property_stock_supplier = inter_comp_location
        po = self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.kit_1.name,
                            "product_id": self.kit_1.id,
                            "product_qty": 1,
                        },
                    )
                ],
            }
        )
        po.action_confirm()

        self.assertTrue(po.picking_ids)
        self.assertEqual(po.line_ids.qty_transferred, 0)

        picking = po.picking_ids
        for move in picking.move_ids:
            move.write({"quantity": move.product_uom_qty, "picked": True})
        picking.button_validate()

        self.assertEqual(po.line_ids.qty_transferred, 1)

    def test_purchase_kit_bill_before_reception_values_each_component(self):
        avco_category = self.env["product.category"].create(
            {
                "name": "AVCO",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            },
        )
        kit_product = self.env["product.product"].create(
            {
                "name": "Kit",
                "is_storable": True,
                "bill_policy": "ordered",
                "standard_price": 10,
                "categ_id": avco_category.id,
            },
        )
        components = self.env["product.product"].create(
            [
                {
                    "name": f"comp {i}",
                    "is_storable": True,
                    "bill_policy": "ordered",
                    "standard_price": 5,
                    "categ_id": avco_category.id,
                }
                for i in (1, 2)
            ],
        )
        self.env["mrp.bom"].create(
            {
                "type": "phantom",
                "product_id": kit_product.id,
                "product_tmpl_id": kit_product.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    Command.create({"product_id": comp.id, "product_qty": 1})
                    for comp in components
                ],
            },
        )
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": kit_product.id,
                            "product_qty": 1,
                            "price_unit": 10.0,
                            "tax_ids": [],
                        },
                    )
                ],
            },
        )
        purchase_order.action_confirm()
        purchase_order.create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()

        valuation_account = avco_category.property_stock_valuation_account_id
        valuation_lines = self.env["account.move.line"].search(
            [("account_id", "=", valuation_account.id)],
        )
        self.assertRecordValues(
            valuation_lines,
            [{"product_id": kit_product.id, "debit": 10.0, "credit": 0.0}],
        )

        purchase_order.picking_ids.button_validate()
        self.assertEqual(
            self.env["account.move.line"].search_count(
                [("account_id", "=", valuation_account.id)],
            ),
            1,
            "validating the receipt must not post the value a second time",
        )
        self.assertEqual(
            purchase_order.picking_ids.move_ids.mapped("value"),
            [5.0, 5.0],
            "the two components should split the kit's billed value",
        )

    def test_mto_component_quantity_reduction_propagation(self):
        self.env.ref("stock.route_warehouse0_mto").active = True
        route_buy = self.warehouse.buy_pull_id.route_id
        route_mto = self.warehouse.mto_pull_id.route_id
        route_mto.rule_ids.procure_method = "make_to_order"
        self.component_a.write(
            {
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner_a.id},
                    )
                ],
                "route_ids": [
                    Command.link(route_buy.id),
                    Command.link(route_mto.id),
                ],
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.component_b.id,
                "product_qty": 1.0,
                "move_raw_ids": [
                    Command.create(
                        {
                            "product_id": self.component_a.id,
                            "product_uom_qty": 5,
                        }
                    )
                ],
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.purchase_order_count, 1)
        self.assertEqual(
            mo.production_group_id.move_ids.created_purchase_line_ids.product_qty,
            5,
        )
        mo.move_raw_ids.product_uom_qty = 2
        self.assertEqual(
            mo.production_group_id.move_ids.created_purchase_line_ids.product_qty,
            2,
        )

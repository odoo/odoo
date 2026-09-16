from odoo.tests import Form

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSaleDropshippingFlows(TestMrpSubcontractingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier = cls.env["res.partner"].create({"name": "Supplier"})
        cls.customer = cls.env["res.partner"].create({"name": "Customer"})
        cls.dropship_route = cls.env.ref("stock_dropshipping.route_drop_shipping")

    def test_dropship_with_different_suppliers(self):
        partners = self.env["res.partner"].create(
            [{"name": "Vendor %s" % i} for i in range(4)]
        )
        compo01, compo02, compo03, kit = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "type": "consu",
                    "route_ids": [(6, 0, [self.dropship_route.id])],
                    "seller_ids": [(0, 0, {"partner_id": seller.id})],
                }
                for name, seller in zip(
                    ["Compo01", "Compo02", "Compo03", "Kit"], partners, strict=True
                )
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo01.id, "product_qty": 1}),
                    (0, 0, {"product_id": compo02.id, "product_qty": 1}),
                    (0, 0, {"product_id": compo03.id, "product_qty": 1}),
                ],
            }
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "picking_policy": "direct",
                    "line_ids": [
                        (
                            0,
                            0,
                            {"name": kit.name, "product_id": kit.id, "product_qty": 1},
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

        purchase_orders = self.env["purchase.order"].search(
            [("partner_id", "in", partners.ids)]
        )
        purchase_orders.action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

        picking = sale_order.picking_ids.filtered(lambda p: p.partner_id == partners[0])
        picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

        picking = sale_order.picking_ids.filtered(lambda p: p.partner_id == partners[2])
        picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

        sale_order.picking_ids.filtered(
            lambda p: p.partner_id == partners[1]
        ).action_cancel()
        self.assertEqual(sale_order.line_ids.qty_transferred, 1)

    def test_return_kit_and_delivered_qty(self):
        compo, kit = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "type": "consu",
                    "route_ids": [(6, 0, [self.dropship_route.id])],
                    "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
                }
                for n in ["Compo", "Kit"]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo.id, "product_qty": 1}),
                ],
            }
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "picking_policy": "direct",
                    "line_ids": [
                        (
                            0,
                            0,
                            {"name": kit.name, "product_id": kit.id, "product_qty": 1},
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        sale_order._get_purchase_orders().action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)

        picking = sale_order.picking_ids
        picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 1.0)

        for case in ["return", "deliver again"]:
            delivered_before_case = 1.0 if case == "return" else 0.0
            delivered_after_case = 0.0 if case == "return" else 1.0
            return_form = Form(
                self.env["stock.return.picking"].with_context(
                    active_ids=[picking.id],
                    active_id=picking.id,
                    active_model="stock.picking",
                )
            )
            with return_form.product_return_moves.edit(0) as line_form:
                line_form.quantity = 1.0
            return_wizard = return_form.save()
            action = return_wizard.action_create_returns()
            picking = self.env["stock.picking"].browse(action["res_id"])
            self.assertEqual(
                sale_order.line_ids.qty_transferred,
                delivered_before_case,
                "Incorrect delivered qty for case '%s'" % case,
            )

            picking.button_validate()
            self.assertEqual(
                sale_order.line_ids.qty_transferred,
                delivered_after_case,
                "Incorrect delivered qty for case '%s'" % case,
            )

    def test_partial_return_kit_and_delivered_qty(self):
        compo, kit = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "type": "consu",
                    "route_ids": [(6, 0, [self.dropship_route.id])],
                    "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
                }
                for n in ["Compo", "Kit"]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo.id, "product_qty": 4}),
                ],
            }
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "picking_policy": "direct",
                    "line_ids": [
                        (
                            0,
                            0,
                            {"name": kit.name, "product_id": kit.id, "product_qty": 1},
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        sale_order._get_purchase_orders().action_confirm()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 0/4"
        )

        picking01 = sale_order.picking_ids
        picking01.move_ids.quantity = 2
        picking01.move_ids.picked = True
        Form.from_action(self.env, picking01.button_validate()).save().process()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 2/4"
        )

        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking01.id, active_model="stock.picking"
            )
        )
        wizard = return_form.save()
        wizard.product_return_moves.write({"quantity": 2.0})
        res = wizard.action_create_returns()
        return01 = self.env["stock.picking"].browse(res["res_id"])

        return01.move_ids.quantity = 2
        return01.move_ids.picked = True
        return01.button_validate()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 0/4"
        )

        picking02 = picking01.backorder_ids
        picking02.move_ids.quantity = 1
        picking02.move_ids.picked = True
        Form.from_action(self.env, picking02.button_validate()).save().process()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 1/4"
        )

        picking03 = picking02.backorder_ids
        picking03.move_ids.quantity = 1
        picking03.move_ids.picked = True
        picking03.button_validate()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 2/4"
        )

        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=return01.id, active_model="stock.picking"
            )
        )
        wizard = return_form.save()
        wizard.product_return_moves.write({"quantity": 1.0})
        res = wizard.action_create_returns()
        picking04 = self.env["stock.picking"].browse(res["res_id"])

        picking04.move_ids.quantity = 1
        picking04.move_ids.picked = True
        picking04.button_validate()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 0.0, "Delivered components: 3/4"
        )

        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=return01.id, active_model="stock.picking"
            )
        )
        wizard = return_form.save()
        wizard.product_return_moves.write({"quantity": 1.0})
        res = wizard.action_create_returns()
        picking04 = self.env["stock.picking"].browse(res["res_id"])

        picking04.move_ids.quantity = 1
        picking04.move_ids.picked = True
        picking04.button_validate()
        self.assertEqual(
            sale_order.line_ids.qty_transferred, 1, "Delivered components: 4/4"
        )

    def test_cancelled_picking_and_delivered_qty(self):
        compo, kit = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "type": "consu",
                    "route_ids": [(6, 0, [self.dropship_route.id])],
                    "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
                }
                for n in ["Compo", "Kit"]
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo.id, "product_qty": 1}),
                ],
            }
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "picking_policy": "direct",
                    "line_ids": [
                        (
                            0,
                            0,
                            {"name": kit.name, "product_id": kit.id, "product_qty": 1},
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        self.env["purchase.order"].search([], order="id desc", limit=1).action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)

        sale_order.picking_ids.action_cancel()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)

    def test_sale_kit_with_dropshipped_component(self):
        compo01, compo02, kit = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "type": "consu",
                }
                for n in ["compo01", "compo02", "super kit"]
            ]
        )

        compo02.write(
            {
                "route_ids": [(6, 0, [self.dropship_route.id])],
                "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo01.id, "product_qty": 1}),
                    (0, 0, {"product_id": compo02.id, "product_qty": 1}),
                ],
            }
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer.id,
                    "picking_policy": "direct",
                    "line_ids": [
                        (
                            0,
                            0,
                            {"name": kit.name, "product_id": kit.id, "product_qty": 1},
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        self.env["purchase.order"].search([], order="id desc", limit=1).action_confirm()

        sale_order.picking_ids.move_ids.quantity = 1
        sale_order.picking_ids.move_ids.picked = True
        for picking in sale_order.picking_ids:
            picking.button_validate()

        self.assertEqual(sale_order.line_ids.qty_transferred, 1.0)

    def test_kit_dropshipped_change_qty_SO(self):
        product_a, product_b, final_product = self.env["product.product"].create(
            [
                {
                    "name": p_name,
                    "type": "consu",
                    "is_storable": True,
                    "seller_ids": [
                        (
                            0,
                            0,
                            {
                                "partner_id": self.supplier.id,
                            },
                        )
                    ],
                }
                for p_name in ["Comp 1", "Comp 2", "Final Product"]
            ]
        )
        product_a.route_ids = self.env.ref("stock_dropshipping.route_drop_shipping")
        product_b.route_ids = self.env.ref("stock_dropshipping.route_drop_shipping")
        self.env["mrp.bom"].create(
            {
                "product_id": final_product.id,
                "product_tmpl_id": final_product.product_tmpl_id.id,
                "product_qty": 1,
                "consumption": "flexible",
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": product_a.id, "product_qty": 1}),
                    (0, 0, {"product_id": product_b.id, "product_qty": 1}),
                ],
            }
        )

        partner = self.env["res.partner"].create(
            {
                "name": "Testing Man",
                "email": "another@user.com",
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        sol = self.env["sale.order.line"].create(
            {
                "name": "Order line",
                "product_id": final_product.id,
                "order_id": so.id,
                "product_qty": 25,
            }
        )
        so.action_confirm()
        sol.write({"product_qty": 10})
        self.assertEqual(sol.purchase_line_ids.mapped("product_qty"), [10, 10])

    def test_dropship_move_lines_have_bom_line_id(self):
        compo, kit = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "type": "consu",
                    "route_ids": [(6, 0, [self.dropship_route.id])],
                    "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
                }
                for n in ["Compo", "Kit"]
            ]
        )

        kit_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": compo.id, "product_qty": 1}),
                ],
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "picking_policy": "direct",
                "line_ids": [
                    (0, 0, {"name": kit.name, "product_id": kit.id, "product_qty": 1}),
                ],
            }
        )
        sale_order.action_confirm()
        sale_order._get_purchase_orders().action_confirm()

        picking = sale_order.picking_ids
        picking.button_validate()
        compo_move = sale_order.line_ids.move_ids.filtered(
            lambda sm: sm.product_id == compo
        )
        compo_bom_line = kit_bom.bom_line_ids.filtered(
            lambda bl: bl.product_id == compo
        )
        self.assertTrue(
            compo_move.bom_line_id == compo_bom_line,
            "The bom_line_id on the stock move was set incorrectly",
        )

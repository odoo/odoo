from datetime import date, datetime, timedelta

from odoo import Command
from odoo.tests import Form

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import ProductVariantsCommon


class TestCreatePicking(ProductVariantsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_id = cls.env["res.partner"].create({"name": "Wood Corner Partner"})
        cls.product_id_1 = cls.env["product.product"].create({"name": "Large Desk"})
        cls.product_id_2 = cls.env["product.product"].create(
            {"name": "Conference Chair"}
        )

        cls.user_purchase_user = mail_new_test_user(
            cls.env,
            name="Pauline Poivraisselle",
            login="pauline",
            email="pur@example.com",
            notification_type="inbox",
            groups="purchase.group_purchase_user",
        )

        cls.po_vals = {
            "partner_id": cls.partner_id.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": cls.product_id_1.name,
                        "product_id": cls.product_id_1.id,
                        "product_qty": 5.0,
                        "product_uom_id": cls.product_id_1.uom_id.id,
                        "price_unit": 500.0,
                    },
                )
            ],
        }

    def test_00_create_picking(self):

        self.po = self.env["purchase.order"].create(self.po_vals)
        self.assertTrue(self.po, "Purchase: no purchase order created")

        self.po.action_confirm()
        self.assertEqual(
            self.po.state, "done", 'Purchase: PO state should be "Purchase'
        )
        self.assertEqual(
            self.po.count_transfer_incoming,
            1,
            "Purchase: one picking should be created",
        )
        self.assertEqual(
            len(self.po.line_ids.move_ids), 1, "One move should be created"
        )
        self.po.line_ids.write({"product_qty": 7.0})
        self.assertEqual(
            len(self.po.line_ids.move_ids), 1, "The two moves should be merged in one"
        )

        self.picking = self.po.picking_ids[0]
        self.picking.move_ids.picked = True
        self.picking._action_done()
        self.assertEqual(
            self.po.line_ids.mapped("qty_transferred"),
            [7.0],
            "Purchase: all products should be received",
        )

        self.po.write(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_id_2.name,
                            "product_id": self.product_id_2.id,
                            "product_qty": 5.0,
                            "product_uom_id": self.product_id_2.uom_id.id,
                            "price_unit": 250.0,
                        },
                    )
                ]
            }
        )
        self.assertEqual(
            self.po.count_transfer_incoming, 2, "New picking should be created"
        )
        moves = self.po.line_ids.mapped("move_ids").filtered(
            lambda x: x.state not in ("done", "cancel")
        )
        self.assertEqual(len(moves), 1, "One moves should have been created")

    def test_02_check_mto_chain(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        picking_type_out = self.env.ref("stock.picking_type_out")
        picking_type_out.reservation_method = "at_confirm"
        partner = self.env["res.partner"].create({"name": "Jhon"})

        vendor = self.env["res.partner"].create({"name": "Roger"})

        product = self.env["product.product"].create(
            {
                "name": "product",
                "is_storable": True,
                "route_ids": [
                    (4, self.ref("stock.route_warehouse0_mto")),
                    (4, self.ref("purchase_stock.route_warehouse0_buy")),
                ],
                "supplier_taxes_id": [(6, 0, [])],
            }
        )

        seller = self.env["product.supplierinfo"].create(
            {
                "product_id": product.id,
                "partner_id": partner.id,
                "price": 12.0,
            }
        )

        customer_move = self.env["stock.move"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 100.0,
                "procure_method": "make_to_order",
                "picking_type_id": picking_type_out.id,
            }
        )

        customer_move._action_confirm()

        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )
        self.assertTrue(purchase_order, "No purchase order created.")

        purchase_order_line = purchase_order.line_ids
        self.assertEqual(
            purchase_order_line.product_id,
            product,
            "The product on the purchase order line is not correct.",
        )
        self.assertEqual(
            purchase_order_line.price_unit,
            seller.price,
            "The purchase order line price should be the same as the seller.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            customer_move.product_uom_qty,
            "The purchase order line qty should be the same as the move.",
        )
        self.assertEqual(
            purchase_order_line.price_subtotal,
            1200.0,
            "The purchase order line subtotal should be equal to the move qty * seller price.",
        )

        purchase_order.action_cancel()
        self.assertEqual(
            purchase_order.state, "cancel", "Purchase order should be cancelled."
        )
        self.assertEqual(
            customer_move.procure_method,
            "make_to_stock",
            "Customer move should be passed to mts.",
        )

        purchase = purchase_order.create(
            {
                "partner_id": vendor.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 100.0,
                            "product_uom_id": product.uom_id.id,
                            "price_unit": 11.0,
                        },
                    )
                ],
            }
        )
        self.assertTrue(purchase, "RFQ should be created")
        purchase.action_confirm()

        picking = purchase.picking_ids
        self.assertTrue(picking, "Picking should be created")

        picking.action_confirm()
        picking.move_ids.quantity = 100.0
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(
            customer_move.state,
            "assigned",
            "Automatically assigned due to the incoming move makes it available.",
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(product, stock_location),
            0.0,
            "Wrong quantity in stock.",
        )

    def test_03_uom(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")

        self.assertEqual(self.product_id_1.uom_id.id, uom_unit.id)

        self.env.user.group_ids += self.env.ref("uom.group_uom")

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_id
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product_id_1
            po_line.product_qty = 1
            po_line.product_uom_id = uom_dozen
        po = po_form.save()
        po.action_confirm()

        move1 = po.picking_ids.move_ids.sorted()[0]
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 12)

        po.line_ids.product_qty = 2
        move1 = po.picking_ids.move_ids.sorted()[0]
        self.assertEqual(move1.product_uom_qty, 24)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 24)

        self.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
        with po_form.line_ids.edit(0) as po_line:
            po_line.product_qty = 3
        po_form.save()
        move2 = po.picking_ids.move_ids.filtered(
            lambda m: m.product_uom_id.id == uom_dozen.id
        )
        self.assertEqual(move2.product_uom_qty, 1)
        self.assertEqual(move2.product_uom_id.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 12)

        move1.quantity = 24
        move1.picked = True
        move2.quantity = 1
        move2.picked = True

        po.picking_ids.button_validate()

        self.assertEqual(po.line_ids.qty_transferred, 3.0)

    def test_mtso_multi_reference_order(self):
        partner_demo_customer = self.partner_id
        final_location = partner_demo_customer.property_stock_customer
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        mto_route = self.env.ref("stock.route_warehouse0_mto")
        mto_route.active = True
        mto_route.rule_ids.procure_method = "mts_else_mto"
        self.product_id_1 = self.env["product.product"].create(
            {
                "name": "ProductA",
                "is_storable": True,
                "route_ids": [
                    (4, self.ref("stock.route_warehouse0_mto")),
                    (4, self.ref("purchase_stock.route_warehouse0_buy")),
                ],
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_id.id,
                            "min_qty": 5,
                            "price": 250,
                        }
                    )
                ],
            }
        )

        ref1, ref2 = self.env["stock.reference"].create(
            [
                {
                    "name": "ref 1",
                },
                {
                    "name": "ref 2",
                },
            ]
        )

        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    self.product_id_1,
                    2.0,
                    self.product_id_1.uom_id,
                    final_location,
                    "test_mtso_mts_1",
                    "test_mtso_mts_1",
                    warehouse.company_id,
                    {
                        "warehouse_id": warehouse,
                        "reference_ids": ref1,
                    },
                ),
                self.env["stock.rule"].Procurement(
                    self.product_id_1,
                    2.0,
                    self.product_id_1.uom_id,
                    final_location,
                    "test_mtso_mts_2",
                    "test_mtso_mts_2",
                    warehouse.company_id,
                    {
                        "warehouse_id": warehouse,
                        "reference_ids": ref2,
                    },
                ),
            ]
        )

        lines = self.env["purchase.order.line"].search(
            [
                ("product_id", "=", self.product_id_1.id),
            ]
        )
        lines.order_id.action_confirm()
        self.assertEqual(len(lines.order_id), 2)

        lines[1].move_ids.picking_id.button_validate()
        reserved_delivery = self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_id_1.id),
                ("picking_type_id", "=", self.ref("stock.picking_type_out")),
                ("state", "=", "assigned"),
            ]
        )
        self.assertEqual(len(reserved_delivery), 1)
        self.assertEqual(
            reserved_delivery.reference_ids, lines[1].order_id.reference_ids
        )

    def test_04_mto_multiple_po(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        picking_type_out = self.env.ref("stock.picking_type_out")
        partner = self.env["res.partner"].create({"name": "Jhon"})

        product = self.env["product.product"].create(
            {
                "name": "product",
                "is_storable": True,
                "route_ids": [
                    (4, self.ref("stock.route_warehouse0_mto")),
                    (4, self.ref("purchase_stock.route_warehouse0_buy")),
                ],
            }
        )

        seller = self.env["product.supplierinfo"].create(
            {
                "product_id": product.id,
                "partner_id": partner.id,
                "price": 12.0,
            }
        )

        customer_picking = self.env["stock.picking"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "partner_id": partner.id,
                "picking_type_id": picking_type_out.id,
            }
        )

        customer_move = self.env["stock.move"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 80.0,
                "procure_method": "make_to_order",
                "picking_id": customer_picking.id,
            }
        )
        customer_picking.action_confirm()

        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )
        self.assertTrue(purchase_order, "No purchase order created.")

        purchase_order_line = purchase_order.line_ids
        self.assertEqual(
            purchase_order_line.product_id,
            product,
            "The product on the purchase order line is not correct.",
        )
        self.assertEqual(
            purchase_order_line.price_unit,
            seller.price,
            "The purchase order line price should be the same as the seller.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            customer_move.product_uom_qty,
            "The purchase order line qty should be the same as the move.",
        )

        purchase_order.action_confirm()

        customer_move_2 = self.env["stock.move"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 20.0,
                "procure_method": "make_to_order",
                "picking_id": customer_picking.id,
            }
        )

        customer_move_2._action_confirm()

        self.assertTrue(
            customer_move_2.exists(),
            "The second customer move should not be merged in the first.",
        )
        self.assertEqual(
            sum(customer_picking.move_ids.mapped("product_uom_qty")), 100.0
        )

        purchase_order_2 = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id), ("state", "=", "draft")]
        )
        self.assertTrue(purchase_order_2, "No purchase order created.")

        purchase_order_2.action_confirm()

        purchase_order.picking_ids.move_ids.quantity = 80.0
        purchase_order.picking_ids.move_ids.picked = True
        purchase_order.picking_ids.button_validate()

        purchase_order_2.picking_ids.move_ids.quantity = 20.0
        purchase_order_2.picking_ids.move_ids.picked = True
        purchase_order_2.picking_ids.button_validate()

        self.assertEqual(
            sum(customer_picking.move_ids.mapped("quantity")),
            100.0,
            "The total quantity for the customer move should be available and reserved.",
        )

    def test_04_rounding(self):
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0
        uom_unit = self.env.ref("uom.product_uom_unit")
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        po = self.env["purchase.order"].create(self.po_vals)

        po.line_ids.product_qty = 1.2
        po.action_confirm()

        move1 = po.picking_ids.move_ids[0]
        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 1.0)

        po.line_ids.product_qty = 2.4
        self.assertEqual(move1.product_uom_qty, 2.0)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 2.0)

        move1.quantity = 2.0
        move1.picked = True
        po.picking_ids.button_validate()

        self.assertEqual(po.line_ids.qty_transferred, 2.0)

    def test_05_uom_rounding(self):
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        po = self.env["purchase.order"].create(self.po_vals)

        po.line_ids.product_uom_id = uom_dozen.id
        po.line_ids.product_qty = 1.3
        po.action_confirm()

        move1 = po.picking_ids.move_ids[0]
        self.assertEqual(move1.product_uom_qty, 12.0)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 12.0)

        self.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
        po.line_ids.product_qty = 2.6
        move2 = po.picking_ids.move_ids.filtered(
            lambda m: m.product_uom_id.id == uom_dozen.id
        )
        self.assertEqual(move2.product_uom_qty, 2)
        self.assertEqual(move2.product_uom_id.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 24)

    def create_delivery_order(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        unit = self.ref("uom.product_uom_unit")
        picking_type_out = self.env.ref("stock.picking_type_out")
        partner = self.env["res.partner"].create(
            {"name": "AAA", "email": "from.test@example.com"}
        )

        warehouse1 = self.env.ref("stock.warehouse0")
        route_buy = warehouse1.buy_pull_id.route_id
        route_mto = warehouse1.mto_pull_id.route_id

        product = self.env["product.product"].create(
            {
                "name": "Usb Keyboard",
                "is_storable": True,
                "uom_id": unit,
                "route_ids": [(6, 0, [route_buy.id, route_mto.id])],
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "product_id": product.id,
                "partner_id": partner.id,
                "price": 50,
            }
        )

        delivery_order = self.env["stock.picking"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "partner_id": partner.id,
                "picking_type_id": picking_type_out.id,
            }
        )

        self.env["stock.move"].create(
            {
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10.0,
                "procure_method": "make_to_order",
                "picking_id": delivery_order.id,
            }
        )

        delivery_order.action_confirm()
        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )

        return delivery_order, purchase_order

    def test_05_propagate_deadline(self):
        delivery_order, purchase_order = self.create_delivery_order()

        self.assertTrue(purchase_order, "No purchase order created.")

        purchase_order_line = purchase_order.line_ids

        purchase_order_line.write(
            {"date_commitment": purchase_order_line.date_commitment + timedelta(days=5)}
        )

        self.assertNotEqual(
            purchase_order_line.date_commitment,
            delivery_order.date_planned,
            "Scheduled delivery order date should not changed.",
        )
        self.assertEqual(
            purchase_order_line.date_commitment,
            delivery_order.date_deadline,
            "Delivery deadline date should be changed.",
        )

    def test_07_differed_schedule_date(self):
        self.env.user.group_ids += self.env.ref("stock.group_adv_location")
        warehouse = self.env["stock.warehouse"].search([], limit=1)

        with Form(warehouse) as w:
            w.reception_steps = "three_steps"
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_id
        with po_form.line_ids.new() as line:
            line.product_id = self.product_id_1
            line.date_commitment = datetime.today()
            line.product_qty = 1.0
        with po_form.line_ids.new() as line:
            line.product_id = self.product_id_1
            line.date_commitment = datetime.today() + timedelta(days=7)
            line.product_qty = 1.0
        po = po_form.save()

        po.action_confirm()

        po.picking_ids.move_line_ids.write({"quantity": 1.0, "picked": True})
        po.picking_ids.button_validate()

        pickings = self.env["stock.picking"].search(
            [("reference_ids", "=", po.reference_ids.id)]
        )
        for picking in pickings:
            self.assertEqual(picking.date_planned.date(), date.today())

    def test_update_quantity_and_return(self):
        po = self.env["purchase.order"].create(self.po_vals)

        po.line_ids.product_qty = 10
        po.action_confirm()

        first_picking = po.picking_ids
        first_picking.move_ids.quantity = 5
        first_picking.move_ids.picked = True
        Form.from_action(self.env, first_picking.button_validate()).save().process()

        self.assertEqual(len(po.picking_ids), 2)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=first_picking.ids,
                active_id=first_picking.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.action_assign()
        return_pick.move_ids.quantity = 2
        return_pick.move_ids.picked = True
        return_pick._action_done()

        self.assertEqual(po.line_ids.qty_transferred, 3)

        po.line_ids.product_qty += 2
        backorder = po.picking_ids.filtered(lambda picking: picking.state == "assigned")
        self.assertEqual(backorder.move_ids.product_uom_qty, 9)

    def test_08_check_update_qty_mto_chain(self):
        def create_run_procurement(product, product_qty, values=None):
            if not values:
                values = {
                    "warehouse_id": picking_type_out.warehouse_id,
                    "action": "pull_push",
                    "reference_ids": reference,
                }
            return self.env["stock.rule"].run(
                [
                    self.env["stock.rule"].Procurement(
                        product,
                        product_qty,
                        self.uom_unit,
                        vendor.property_stock_customer,
                        product.name,
                        "/",
                        self.env.company,
                        values,
                    )
                ]
            )

        picking_type_out = self.env.ref("stock.picking_type_out")
        partner = self.env["res.partner"].create({"name": "Jhon"})
        vendor = self.env["res.partner"].create({"name": "Roger"})
        self.env["stock.route"].browse(
            self.ref("stock.route_warehouse0_mto")
        ).action_unarchive()
        self.env["stock.route"].browse(
            self.ref("stock.route_warehouse0_mto")
        ).rule_ids.procure_method = "make_to_order"
        product = self.env["product.product"].create(
            {
                "name": "product",
                "is_storable": True,
                "route_ids": [
                    (4, self.ref("stock.route_warehouse0_mto")),
                    (4, self.ref("purchase_stock.route_warehouse0_buy")),
                ],
                "supplier_taxes_id": [(6, 0, [])],
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "product_id": product.id,
                "partner_id": partner.id,
                "price": 12.0,
            }
        )

        reference = self.env["stock.reference"].create({"name": "reference"})
        create_run_procurement(
            product,
            50,
            {
                "reference_ids": reference,
                "warehouse_id": picking_type_out.warehouse_id,
                "partner_id": vendor.id,
            },
        )
        customer_move = self.env["stock.move"].search([("product_id", "=", product.id)])
        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )
        self.assertTrue(purchase_order, "No purchase order created.")

        purchase_order_line = purchase_order.line_ids
        self.assertEqual(
            purchase_order_line.product_id,
            product,
            "The product on the purchase order line is not correct.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            50,
            "The purchase order line qty should be the same as the move.",
        )

        create_run_procurement(product, -10.00)
        self.assertEqual(
            customer_move.product_uom_qty,
            40,
            "The demand on the initial move should have been decreased when merged with the procurement.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            40,
            "The demand on the Purchase Order should have been decreased since it is still a RFQ.",
        )

        create_run_procurement(product, 5.00)
        self.assertEqual(
            customer_move.product_uom_qty,
            45,
            "The demand on the initial move should have been increased when merged with the procurement.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            45,
            "The demand on the Purchase Order should have been increased since it is still a RFQ.",
        )

        purchase_order.action_confirm()
        create_run_procurement(product, -10.00)
        self.assertEqual(
            customer_move.product_uom_qty,
            35,
            "The demand on the initial move should have been decreased when merged with the procurement.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            45,
            "The demand on the Purchase Order should not have been decreased since it is has been confirmed.",
        )
        purchase_orders = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )
        self.assertEqual(
            len(purchase_orders),
            1,
            "No RFQ should have been created for a negative demand",
        )

        create_run_procurement(product, 5.00)
        self.assertEqual(
            customer_move.product_uom_qty,
            35,
            "The demand on the initial move should not have been increased since it should be a new move.",
        )
        self.assertEqual(
            purchase_order_line.product_qty,
            45,
            "The demand on the Purchase Order should not have been increased since it is has been confirmed.",
        )
        purchase_orders = self.env["purchase.order"].search(
            [("partner_id", "=", partner.id)]
        )
        self.assertEqual(
            len(purchase_orders),
            2,
            "A new RFQ should have been created for missing demand.",
        )

    def test_update_qty_purchased(self):
        stock_valuation_account = self.env["account.account"].create(
            {
                "name": "Stock Valuation",
                "code": "STOCKVAL",
                "account_type": "asset_current",
            }
        )
        product_categ = self.env["product.category"].create(
            {
                "name": "Stock Category",
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
                "property_stock_valuation_account_id": stock_valuation_account.id,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Storable Product",
                "is_storable": True,
                "categ_id": product_categ.id,
                "standard_price": 15.0,
            }
        )

        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 10,
                            "product_uom_id": product.uom_id.id,
                            "price_unit": 15.0,
                        },
                    )
                ],
            }
        )

        purchase_order.action_confirm()
        self.assertEqual(
            purchase_order.state, "done", "Purchase order should be in purchase state."
        )
        self.assertEqual(len(purchase_order.picking_ids), 1)
        self.assertEqual(purchase_order.line_ids.price_unit, 15)
        self.assertEqual(purchase_order.picking_ids.move_ids.price_unit, 15)
        purchase_order.line_ids.product_qty = 9
        self.assertEqual(len(purchase_order.picking_ids), 1)
        self.assertEqual(len(purchase_order.picking_ids.move_ids), 1)
        self.assertEqual(
            purchase_order.picking_ids.move_line_ids.quantity_product_uom, 9
        )

    def test_return_to_vendor_multi_step(self):
        self.env.user.group_ids += self.env.ref("stock.group_stock_multi_locations")
        self.env.user.group_ids += self.env.ref("stock.group_adv_location")
        warehouse = self.env["stock.warehouse"].search([], limit=1)

        with Form(warehouse) as w:
            w.reception_steps = "three_steps"

        vendor_returns_loc = self.env["stock.location"].create(
            {
                "name": "Vendor returns processing",
                "usage": "internal",
                "location_id": warehouse.view_location_id.id,
            }
        )

        self.env["stock.rule"].create(
            {
                "name": "Vendor returns",
                "route_id": warehouse.reception_route_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_src_id": vendor_returns_loc.id,
                "action": "push",
                "auto": "manual",
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
            }
        )

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_id
        with po_form.line_ids.new() as line:
            line.product_id = self.product_id_1
            line.product_qty = 10
        po = po_form.save()
        po.action_confirm()
        first_picking = po.picking_ids
        first_picking.move_ids.quantity = 10
        first_picking.move_ids.picked = True
        first_picking.button_validate()
        second_picking = first_picking.move_ids.move_dest_ids.picking_id
        second_picking.move_ids.quantity = 10
        second_picking.move_ids.picked = True
        second_picking.button_validate()

        self.assertEqual(po.line_ids.qty_transferred, 10)

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=second_picking.ids,
                active_id=second_picking.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking_form.product_return_moves._records[0]["quantity"] = 2
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.action_assign()
        return_pick.location_dest_id = vendor_returns_loc
        return_pick.move_ids.quantity = 2
        return_pick.move_ids.picked = True
        return_pick._action_done()
        push_pick = return_pick.move_ids.move_dest_ids.picking_id
        push_pick.action_assign()
        push_pick.move_ids.quantity = 2
        push_pick.move_ids.picked = True
        push_pick._action_done()

        self.assertEqual(po.line_ids.qty_transferred, 8)
        self.assertEqual(push_pick.partner_id, po.partner_id)

    def test_create_return_exchange_with_no_picking_origin(self):
        self.product_id_2.seller_ids = [
            (
                0,
                0,
                {
                    "partner_id": self.partner_id.id,
                    "price": 10,
                },
            )
        ]
        stock_picking = self.env["stock.picking"].create(
            {
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_id_2.id,
                            "product_uom_qty": 10,
                            "product_uom_id": self.product_id_2.uom_id.id,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_stock"
                            ).id,
                        },
                    )
                ],
            }
        )
        stock_picking.button_validate()

        stock_return_picking = (
            self.env["stock.return.picking"]
            .with_context(
                active_ids=stock_picking.ids,
                active_id=stock_picking.ids[0],
                active_model="stock.picking",
            )
            .create({})
        )

        stock_return_picking.product_return_moves.quantity = 1.0
        res = stock_return_picking.action_create_exchanges()
        exchange_return_picking = self.env["stock.picking"].browse(res["res_id"])

        self.assertTrue(exchange_return_picking)
        self.assertEqual(
            exchange_return_picking.origin, "Return of " + stock_picking.name
        )

    def test_po_with_return_for_exchange_shows_3_transfers(self):
        po = self.env["purchase.order"].create(self.po_vals)
        po.action_confirm()

        stock_picking = po.picking_ids
        stock_picking.button_validate()

        return_picking_wizard = (
            self.env["stock.return.picking"]
            .with_context(
                active_ids=stock_picking.ids,
                active_id=stock_picking.id,
                active_model="stock.picking",
            )
            .create({})
        )

        return_picking_wizard.product_return_moves.quantity = 1.0
        return_picking_wizard.action_create_exchanges()

        self.assertEqual(
            po.count_transfer_incoming,
            3,
            "All 3 transfers (orig, return, exchange) should be associated with the PO.",
        )

        picking_type_out = self.env.ref("stock.picking_type_out")
        picking_type_in = self.env.ref("stock.picking_type_in")

        self.assertEqual(po.picking_ids[0].picking_type_id, picking_type_in)
        self.assertEqual(po.picking_ids[0].move_ids.quantity, 5)
        self.assertEqual(po.picking_ids[1].picking_type_id, picking_type_out)
        self.assertEqual(po.picking_ids[1].move_ids.quantity, 1)
        self.assertEqual(po.picking_ids[2].picking_type_id, picking_type_in)
        self.assertEqual(po.picking_ids[2].move_ids.quantity, 1)

    def test_move_description(self):
        product_matrix_installed = (
            "purchase_product_matrix"
            in self.env["ir.module.module"]._get_installed_module_ids()
        )
        attribute_vals = [
            {
                "attribute_id": self.color_attribute.id,
                "value_ids": [Command.set(self.color_attribute.value_ids.ids)],
            }
        ]
        if product_matrix_installed:
            attribute_vals.append(
                {
                    "attribute_id": self.no_variant_attribute.id,
                    "value_ids": [Command.set(self.no_variant_attribute.value_ids.ids)],
                }
            )
        product_with_description = self.env["product.template"].create(
            {
                "name": "Product with description",
                "description_pickingin": "Receive with care",
                "description_purchase": "Purchase description",
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_id.id,
                            "product_name": "ABC",
                            "product_code": "123",
                            "min_qty": 1,
                            "price": 1,
                        }
                    )
                ],
                "attribute_line_ids": [Command.create(val) for val in attribute_vals],
            }
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product_with_description.product_variant_ids.filtered(
                                lambda p: (
                                    p.product_template_attribute_value_ids.name == "red"
                                )
                            ).id,
                            "product_no_variant_attribute_value_ids": product_matrix_installed
                            and [
                                Command.set(
                                    product_with_description.attribute_line_ids[1]
                                    .product_template_value_ids[0]
                                    .ids
                                )
                            ],
                            "product_qty": 1,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(
            po.line_ids.name,
            "[123] ABC (red)\nPurchase description"
            + ("\nNo variant: extra" if product_matrix_installed else ""),
        )
        po.line_ids.name += "\nRandom purchase notes"
        po.action_confirm()
        self.assertEqual(
            po.picking_ids.move_ids.description_picking,
            ("No variant: extra\n" if product_matrix_installed else "")
            + "[123] ABC\nReceive with care",
        )

    def test_receipt_return_type_change_qty_transferred(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_ship"
        warehouse.in_type_id.return_picking_type_id = warehouse.pick_type_id

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_id_1.id,
                            "product_qty": 1.0,
                            "product_uom_id": self.product_id_1.uom_id.id,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        po.action_confirm()
        receipt = po.picking_ids
        receipt.move_ids.quantity = 1.0
        receipt.button_validate()
        self.assertEqual(po.line_ids.qty_transferred, 1.0)

        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(
                active_ids=receipt.ids,
                active_id=receipt.id,
                active_model="stock.picking",
            )
            .create({})
        )
        return_wizard.product_return_moves.quantity = 1.0
        res = return_wizard.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.picking_type_id = warehouse.out_type_id
        return_pick.move_ids.quantity = 1.0
        return_pick.button_validate()

        self.assertEqual(po.line_ids.qty_transferred, 0.0)

    def test_average_cost_updated_after_po_with_discount(self):
        self.env["product.value"].search(
            [("product_id", "=", self.product_id_1.id)]
        ).unlink()
        self.product_id_1.categ_id = self.env["product.category"].create(
            {
                "name": "average",
                "property_cost_method": "average",
            }
        )
        self.product_id_1.seller_ids = [
            Command.create(
                {
                    "partner_id": self.partner_id.id,
                    "min_qty": 10,
                    "price": 500.0,
                    "discount": 10,
                }
            )
        ]
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_id_1.name,
                            "product_id": self.product_id_1.id,
                            "product_qty": 5.0,
                            "product_uom_id": self.product_id_1.uom_id.id,
                        },
                    )
                ],
            }
        )
        po.action_confirm()
        with Form(po) as po_form:
            with po_form.line_ids.edit(0) as po_line:
                po_line.product_qty = 10.0
        self.assertEqual(po.line_ids.discount, 10)
        po.picking_ids.button_validate()
        self.assertEqual(self.product_id_1.standard_price, 450.0)

    def test_view_picking_context_omits_default_origin(self):
        """A transfer built from the PO's transfer list is not the PO's own.

        The list is reached from the order, but «New» there creates an unrelated
        transfer. Pre-filling its Source Document with the order name makes that
        transfer claim an origin it does not have: `origin` is trigram-indexed
        and feeds the move reference, so the stray transfer then shows up when
        searching for the order.
        """
        po = self.env["purchase.order"].create(self.po_vals)
        po.action_confirm()

        action = po._get_action_view_picking(po.picking_ids)

        self.assertNotIn("default_origin", action["context"])
        new_picking = (
            self.env["stock.picking"].with_context(**action["context"]).new({})
        )
        self.assertFalse(new_picking.origin)

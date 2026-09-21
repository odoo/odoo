from datetime import datetime as dt
from datetime import timedelta as td
from json import loads

from odoo import SUPERUSER_ID, Command
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Date
from odoo.tests import Form, freeze_time, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import format_date
from odoo.tools.date_utils import add


@tagged("post_install", "-at_install")
@freeze_time("2021-01-14 09:12:15")
class TestReorderingRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("uom.group_uom")
        cls.partner = cls.env["res.partner"].create({"name": "Smith"})
        cls.buy_route = cls.env.ref("purchase_stock.route_warehouse0_buy")
        cls.buy_route.product_selectable = True
        product_form = Form(cls.env["product.product"])
        product_form.name = "Product A"
        product_form.is_storable = True
        product_form.description = "Internal Notes"
        with product_form.seller_ids.new() as seller:
            seller.partner_id = cls.partner
            seller.product_uom_id = product_form.uom_id
        cls.product_01 = product_form.save()
        cls.product_01.route_ids = cls.buy_route

    def test_reordering_rule_1(self):
        warehouse_1 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        warehouse_1.reception_steps = "two_steps"
        warehouse_2 = self.env["stock.warehouse"].create(
            {
                "name": "WH 2",
                "code": "WH2",
                "company_id": self.env.company.id,
                "partner_id": self.env.company.partner_id.id,
                "reception_steps": "one_step",
            }
        )

        user_purchase_id = self.env["res.users"].create(
            {
                "login": "buyer1",
                "name": "Buyer1",
                "email": "buyer1@example.com",
            }
        )
        self.partner.user_purchase_id = user_purchase_id.id

        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = warehouse_1.lot_stock_id
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point = orderpoint_form.save()

        manual_po = self.env["purchase.order"].create(
            {
                "name": "Manual PO",
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_01.id,
                            "product_qty": 10,
                        }
                    )
                ],
            }
        )

        manual_po.action_confirm()
        self.assertEqual(order_point.qty_forecast, 10)

        manual_po.action_cancel()
        self.assertEqual(order_point.qty_forecast, 0)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = self.partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.action_confirm()
        self.env["stock.scheduler"].run()

        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", self.partner.id), ("state", "!=", "cancel")]
        )
        self.assertTrue(purchase_order, "No purchase order created.")
        purchase_order.picking_type_id = warehouse_2.in_type_id
        with self.assertRaises(UserError):
            purchase_order.action_confirm()
        purchase_order.picking_type_id = warehouse_1.in_type_id

        self.assertEqual(
            order_point.name,
            purchase_order.origin,
            "Source document on purchase order should be the name of the reordering rule.",
        )
        self.assertEqual(purchase_order.line_ids.product_qty, 10)
        self.assertEqual(purchase_order.line_ids.name, "Product A")
        self.assertEqual(purchase_order.user_id, user_purchase_id)

        purchase_order.line_ids.product_qty = 12
        purchase_order.action_confirm()

        self.assertEqual(
            purchase_order.picking_ids.move_ids.filtered(
                lambda m: m.product_id == self.product_01
            ).product_qty,
            12,
        )
        purchase_order.picking_ids.button_validate()
        next_picking = purchase_order.picking_ids.move_ids.move_dest_ids.picking_id
        self.assertEqual(len(next_picking), 1)
        self.assertEqual(
            next_picking.move_ids.filtered(
                lambda m: m.product_id == self.product_01
            ).product_qty,
            12,
        )

        purchase_order.line_ids.product_qty = 15
        receipt1, receipt2 = purchase_order.picking_ids
        self.assertEqual(receipt1.move_ids.product_qty, 12)
        self.assertEqual(receipt2.move_ids.product_qty, 3)
        purchase_order.picking_ids[1].button_validate()
        self.assertEqual(next_picking.move_ids.product_qty, 15)

    def test_reordering_rule_2(self):
        self.env.user.group_ids += self.env.ref("stock.group_stock_multi_locations")
        warehouse_1 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        subloc_1 = self.env["stock.location"].create(
            {"name": "subloc_1", "location_id": warehouse_1.lot_stock_id.id}
        )
        subloc_2 = self.env["stock.location"].create(
            {"name": "subloc_2", "location_id": warehouse_1.lot_stock_id.id}
        )

        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = subloc_1
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_1 = orderpoint_form.save()
        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = subloc_2
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_2 = orderpoint_form.save()

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = self.partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids[0].location_id = subloc_1.id
        customer_picking.move_ids[1].location_id = subloc_2.id

        customer_picking.action_confirm()
        self.assertEqual(
            self.product_01.with_context(location=subloc_1.id).qty_available_virtual,
            -10,
        )
        self.assertEqual(
            self.product_01.with_context(location=subloc_2.id).qty_available_virtual,
            -10,
        )

        self.env["stock.scheduler"].run()

        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", self.partner.id)]
        )
        self.assertTrue(purchase_order, "No purchase order created.")
        self.assertEqual(
            len(purchase_order.line_ids), 2, "Not enough purchase order lines created."
        )

        purchase_order.line_ids.filtered(
            lambda pol: pol.orderpoint_id == order_point_1
        ).product_qty = 15
        purchase_order.action_confirm()
        self.assertEqual(
            self.product_01.with_context(location=subloc_1.id).qty_available_virtual, 5
        )
        self.assertEqual(
            self.product_01.with_context(location=subloc_2.id).qty_available_virtual, 0
        )

        purchase_order.line_ids.filtered(
            lambda pol: pol.orderpoint_id == order_point_2
        ).product_qty = 15
        self.assertEqual(
            self.product_01.with_context(location=subloc_1.id).qty_available_virtual, 5
        )
        self.assertEqual(
            self.product_01.with_context(location=subloc_2.id).qty_available_virtual, 5
        )
        self.assertEqual(
            self.product_01.with_context(
                location=warehouse_1.lot_stock_id.id
            ).qty_available_virtual,
            10,
        )

    def test_reordering_rule_3(self):
        warehouse_1 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )

        outside_loc = self.env["stock.location"].create(
            {
                "name": "outside",
                "usage": "internal",
            }
        )
        route = self.env["stock.route"].create(
            {
                "name": "resupply outside",
                "rule_ids": [
                    (
                        0,
                        False,
                        {
                            "name": "Buy",
                            "location_dest_id": warehouse_1.lot_stock_id.id,
                            "company_id": self.env.company.id,
                            "action": "buy",
                            "sequence": 2,
                            "procure_method": "make_to_stock",
                            "picking_type_id": self.env.ref("stock.picking_type_in").id,
                        },
                    ),
                    (
                        0,
                        False,
                        {
                            "name": "ressuply from stock",
                            "location_src_id": warehouse_1.lot_stock_id.id,
                            "location_dest_id": outside_loc.id,
                            "company_id": self.env.company.id,
                            "action": "pull",
                            "procure_method": "mts_else_mto",
                            "sequence": 1,
                            "picking_type_id": self.env.ref(
                                "stock.picking_type_out"
                            ).id,
                        },
                    ),
                ],
            }
        )
        vendor1 = self.env["res.partner"].create(
            {"name": "AAA", "email": "from.test@example.com"}
        )
        product = self.env["product.product"].create(
            {
                "name": "product_rr_3",
                "is_storable": True,
                "route_ids": [(4, route.id)],
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "product_id": product.id,
                "partner_id": vendor1.id,
                "price": 50,
            }
        )

        self.env["res.users"].browse(2).group_ids += self.env.ref(
            "stock.group_stock_multi_locations"
        )
        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"].with_user(2))
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = outside_loc
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_1 = orderpoint_form.save()
        order_point_1.route_id = route
        order_point_1.trigger = "manual"

        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10,
                "location_id": outside_loc.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
            }
        )
        move._action_confirm()

        self.assertEqual(order_point_1.qty_forecast, -10)

        order_point_1.action_replenish()

        purchase_order = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", product.id)])
            .order_id
        )
        self.assertTrue(purchase_order, "No purchase order created.")
        self.assertEqual(
            len(purchase_order.line_ids), 1, "Not enough purchase order lines created."
        )
        purchase_order.action_confirm()

    def test_reordering_rule_4(self):
        warehouse_1 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )

        with self.assertRaises(
            ValidationError,
            msg="The minimum quantity must be less than or equal to the maximum quantity.",
        ):
            self.env["stock.warehouse.orderpoint"].create(
                {
                    "warehouse_id": warehouse_1.id,
                    "location_id": warehouse_1.lot_stock_id.id,
                    "product_id": self.product_01.id,
                    "product_min_qty": 2,
                    "product_max_qty": 1,
                }
            )

    def test_reordering_rule_triggered_two_times(self):
        today = Date.context_today(self.env.user)
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        stock_location = warehouse.lot_stock_id
        out_type = warehouse.out_type_id
        customer_location = self.env.ref("stock.stock_location_customers")

        self.product_01.seller_ids.delay = 3
        rr = self.env["stock.warehouse.orderpoint"].create(
            {
                "location_id": stock_location.id,
                "product_id": self.product_01.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )

        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": out_type.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_01.id,
                            "product_uom_qty": 1,
                            "product_uom_id": self.product_01.uom_id.id,
                            "location_id": stock_location.id,
                            "location_dest_id": customer_location.id,
                        },
                    )
                ],
            }
        )
        delivery.action_confirm()
        self.assertEqual(rr.deadline_date, today - td(days=3))
        delivery.date_planned += td(days=4)
        self.assertEqual(rr.deadline_date, today + td(days=1))

        pol = self.env["purchase.order.line"].search(
            [("product_id", "=", self.product_01.id)]
        )
        self.assertEqual(pol.product_qty, 1.0)
        self.assertEqual(rr.qty_to_order, 0.0)

        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": out_type.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_01.id,
                            "product_uom_qty": 1,
                            "product_uom_id": self.product_01.uom_id.id,
                            "location_id": stock_location.id,
                            "location_dest_id": customer_location.id,
                        },
                    )
                ],
            }
        )
        delivery.action_confirm()

        self.assertEqual(pol.product_qty, 2.0)
        self.assertEqual(rr.qty_to_order, 0.0)

    def test_replenish_report_1(self):
        partner = self.env["res.partner"].create({"name": "Tintin"})
        route_buy = self.env.ref("purchase_stock.route_warehouse0_buy")
        route_mto = self.env.ref("stock.route_warehouse0_mto")

        product_form = Form(self.env["product.product"])
        product_form.name = "Simple Product"
        product_form.is_storable = True
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
            s.product_uom_id = product_form.uom_id
        product = product_form.save()

        product_form = Form(self.env["product.product"])
        product_form.name = "Product BUY + MTO"
        product_form.is_storable = True
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
            s.product_uom_id = product_form.uom_id
        product_buy_mto = product_form.save()
        product_buy_mto.route_ids = route_buy | route_mto

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(
            lambda m: m.product_id == product_buy_mto
        ).procure_method = "make_to_order"
        customer_picking.action_confirm()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()

        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 20.0)
        self.assertEqual(orderpoint_product.trigger, "manual")
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

        orderpoint_product.action_replenish()
        po = self.env["purchase.order"].search([("partner_id", "=", partner.id)])
        self.assertTrue(po)
        self.assertEqual(len(po.line_ids), 2.0)
        po_line_product_mto = po.line_ids.filtered(
            lambda l: l.product_id == product_buy_mto
        )
        po_line_product = po.line_ids.filtered(lambda l: l.product_id == product)
        self.assertEqual(po_line_product_mto.product_uom_qty, 10.0)
        self.assertEqual(po_line_product.product_uom_qty, 20.0)

        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product)
        self.assertFalse(orderpoint_product_mto_buy)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(
            lambda m: m.product_id == product_buy_mto
        ).procure_method = "make_to_order"
        customer_picking.action_confirm()
        self.env["stock.warehouse.orderpoint"].flush_model()

        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 10.0)
        self.assertEqual(orderpoint_product.trigger, "manual")
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

    def test_replenish_report_2(self):
        partner = self.env["res.partner"].create({"name": "Tintin"})
        for wh in self.env["stock.warehouse"].search([]):
            wh.reception_steps = "two_steps"
        route_buy = self.env.ref("purchase_stock.route_warehouse0_buy")
        route_mto = self.env.ref("stock.route_warehouse0_mto")

        product_form = Form(self.env["product.product"])
        product_form.name = "Simple Product"
        product_form.is_storable = True
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
            s.product_uom_id = product_form.uom_id
        product = product_form.save()

        product_form = Form(self.env["product.product"])
        product_form.name = "Product BUY + MTO"
        product_form.is_storable = True
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
            s.product_uom_id = product_form.uom_id
        product_buy_mto = product_form.save()
        product_buy_mto.route_ids = route_buy | route_mto

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(
            lambda m: m.product_id == product_buy_mto
        ).procure_method = "make_to_order"
        customer_picking.action_confirm()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 20.0)
        self.assertEqual(orderpoint_product.trigger, "manual")
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

        orderpoint_product.action_replenish()
        po = self.env["purchase.order"].search([("partner_id", "=", partner.id)])
        self.assertTrue(po)
        self.assertEqual(len(po.line_ids), 2.0)
        po_line_product_mto = po.line_ids.filtered(
            lambda l: l.product_id == product_buy_mto
        )
        po_line_product = po.line_ids.filtered(lambda l: l.product_id == product)
        self.assertEqual(po_line_product_mto.product_uom_qty, 10.0)
        self.assertEqual(po_line_product.product_uom_qty, 20.0)

        self.env["stock.warehouse.orderpoint"].flush_model()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product)
        self.assertFalse(orderpoint_product_mto_buy)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with picking_form.move_ids.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(
            lambda m: m.product_id == product_buy_mto
        ).procure_method = "make_to_order"
        customer_picking.action_confirm()
        self.env["stock.warehouse.orderpoint"].flush_model()

        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint_product = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        orderpoint_product_mto_buy = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_buy_mto.id)]
        )
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 10.0)
        self.assertEqual(orderpoint_product.trigger, "manual")
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

    def test_procure_not_default_partner(self):
        purchase_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        uom_unit = self.env.ref("uom.product_uom_unit")
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        product = self.env["product.product"].create(
            {
                "name": "product TEST",
                "standard_price": 100.0,
                "is_storable": True,
                "uom_id": uom_unit.id,
                "default_code": "A",
                "route_ids": [(6, 0, purchase_route.ids)],
            }
        )
        default_vendor = self.env["res.partner"].create(
            {
                "name": "Supplier A",
            }
        )
        secondary_vendor = self.env["res.partner"].create(
            {
                "name": "Supplier B",
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "partner_id": default_vendor.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "delay": 7,
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "partner_id": secondary_vendor.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "delay": 10,
            }
        )

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(po_line)
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    product,
                    100,
                    uom_unit,
                    warehouse.lot_stock_id,
                    "Test default vendor",
                    "/",
                    self.env.company,
                    {
                        "warehouse_id": warehouse,
                        "date_planned": dt.today() + td(days=15),
                        "rule_id": warehouse.buy_pull_id,
                        "group_id": False,
                        "route_ids": [],
                    },
                )
            ]
        )
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(po_line)
        self.assertEqual(po_line.partner_id, default_vendor)
        po_line.order_id.action_cancel()
        po_line.order_id.unlink()

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(po_line)
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    product,
                    100,
                    uom_unit,
                    warehouse.lot_stock_id,
                    "Test default vendor",
                    "/",
                    self.env.company,
                    {
                        "warehouse_id": warehouse,
                        "date_planned": dt.today() + td(days=15),
                        "rule_id": warehouse.buy_pull_id,
                        "group_id": False,
                        "route_ids": [],
                        "supplierinfo_name": secondary_vendor,
                    },
                )
            ]
        )
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(po_line)
        self.assertEqual(po_line.partner_id, secondary_vendor)

    def test_procure_multi_lingual(self):
        purchase_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": "test warehouse",
                "active": True,
                "reception_steps": "one_step",
                "delivery_steps": "ship_only",
                "code": "TEST",
            }
        )
        customer_loc, _ = warehouse._get_partner_locations()
        mto_rule = self.env["stock.rule"].search(
            [
                ("warehouse_id", "=", warehouse.id),
                ("procure_method", "=", "make_to_order"),
                ("location_dest_id", "=", customer_loc.id),
            ]
        )
        route_mto = self.env["stock.route"].create(
            {
                "name": "MTO",
                "active": True,
                "sequence": 3,
                "product_selectable": True,
                "rule_ids": [(6, 0, [mto_rule.id])],
            }
        )
        uom_unit = self.env.ref("uom.product_uom_unit")
        product = self.env["product.product"].create(
            {
                "name": "product TEST",
                "standard_price": 100.0,
                "is_storable": True,
                "uom_id": uom_unit.id,
                "default_code": "A",
                "route_ids": [
                    (
                        6,
                        0,
                        [
                            route_mto.id,
                            purchase_route.id,
                        ],
                    )
                ],
            }
        )
        self.env["res.lang"]._activate_lang("fr_FR")
        product.product_tmpl_id.with_context(lang="fr_FR").name = "produit en français"
        product.with_context(lang="fr_FR").name = "produit en français"
        default_vendor = self.env["res.partner"].create(
            {
                "name": "Supplier A",
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "partner_id": default_vendor.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "delay": 7,
            }
        )
        customer = self.env["res.partner"].create({"name": "Customer", "lang": "fr_FR"})
        procurement = self.env["stock.rule"].Procurement(
            product,
            100,
            uom_unit,
            customer.property_stock_customer,
            "Test default vendor",
            "/",
            self.env.company,
            {
                "warehouse_id": warehouse,
                "date_planned": dt.today() + td(days=15),
                "route_ids": [],
            },
        )
        self.env.invalidate_all()

        self.env["stock.rule"].run([procurement])

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(po_line)
        self.assertEqual("[A] product TEST", po_line.name)

    def test_multi_lingual_orderpoints(self):
        warehouse = self.env.ref("stock.warehouse0")
        warehouse_2 = self.env["stock.warehouse"].create(
            {
                "name": "Warehouse 2",
                "code": "WH2",
                "resupply_wh_ids": warehouse.ids,
            }
        )
        route_buy_id = self.ref("purchase_stock.route_warehouse0_buy")
        product = self.env["product.product"].create(
            {
                "name": "product TEST",
                "standard_price": 100.0,
                "is_storable": True,
                "uom_id": self.ref("uom.product_uom_unit"),
                "default_code": "A",
                "route_ids": [Command.set([route_buy_id])],
            }
        )
        self.env["res.lang"]._activate_lang("fr_FR")
        product.with_context(lang="fr_FR").name = "produit en français"
        default_vendor = self.env["res.partner"].create(
            {
                "name": "Super Supplier",
                "lang": "fr_FR",
            }
        )
        self.env["product.supplierinfo"].create(
            {
                "partner_id": default_vendor.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "delay": 7,
            }
        )
        warehouse_2.resupply_route_ids.rule_ids.procure_method = "make_to_order"
        orderpoint, dummy = self.env["stock.warehouse.orderpoint"].create(
            [
                {
                    "name": "RR for %s" % product.name,
                    "warehouse_id": warehouse_2.id,
                    "location_id": warehouse_2.lot_stock_id.id,
                    "trigger": "auto",
                    "product_id": product.id,
                    "route_id": warehouse_2.resupply_route_ids.id,
                    "qty_to_order_manual": 5.0,
                },
                {
                    "name": "RR for %s" % "Dummy",
                    "warehouse_id": self.ref("stock.warehouse0"),
                    "location_id": self.env.ref("stock.warehouse0").lot_stock_id.id,
                    "trigger": "auto",
                    "product_id": self.product_01.id,
                    "route_id": route_buy_id,
                },
            ]
        )
        french_user = self.env["res.users"].create(
            {
                "login": "french user",
                "name": "Arnold",
                "email": "frenchuser@example.com",
                "lang": "fr_FR",
                "group_ids": [Command.set(self.env.user.group_ids.ids)],
            }
        )
        self.env.company.partner_id.lang = "fr_FR"
        orderpoint.with_user(french_user).action_replenish()

        po_line = self.env["purchase.order.line"].search(
            [("partner_id", "=", default_vendor.id), ("product_id", "=", product.id)],
            limit=1,
        )
        self.assertRecordValues(
            po_line, [{"name": "[A] produit en français", "product_qty": 5.0}]
        )
        self.assertRecordValues(po_line.move_dest_ids, [{"product_uom_qty": 5.0}])
        orderpoint.qty_to_order_manual = 4.0
        orderpoint.with_user(french_user).action_replenish()
        self.assertRecordValues(
            po_line, [{"name": "[A] produit en français", "product_qty": 9.0}]
        )
        self.assertEqual(len(po_line.order_id.line_ids), 1)
        self.assertRecordValues(
            po_line.move_dest_ids, [{"product_uom_qty": 5.0}, {"product_uom_qty": 4.0}]
        )
        orderpoint.product_min_qty = 10.0
        orderpoint.product_max_qty = 20.0
        (orderpoint | dummy).invalidate_recordset()
        self.env["stock.scheduler"].run()
        self.assertRecordValues(
            po_line, [{"name": "[A] produit en français", "product_qty": 20.0}]
        )
        self.assertEqual(len(po_line.order_id.line_ids), 1)

    def test_multi_locations_and_reordering_rule(self):
        self.env.user.group_ids += self.env.ref("stock.group_stock_multi_locations")
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        stock_location = warehouse.lot_stock_id
        sub_location = self.env["stock.location"].create(
            {"name": "subloc_1", "location_id": stock_location.id}
        )

        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.warehouse_id = warehouse
        orderpoint_form.location_id = stock_location
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 1
        orderpoint_form.product_max_qty = 1
        stock_op = orderpoint_form.save()

        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.warehouse_id = warehouse
        orderpoint_form.location_id = sub_location
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 2
        orderpoint_form.product_max_qty = 2
        sub_op = orderpoint_form.save()

        stock_op.action_replenish()
        sub_op.action_replenish()

        po = self.env["purchase.order"].search([("partner_id", "=", self.partner.id)])
        self.assertRecordValues(
            po.line_ids,
            [
                {
                    "product_id": self.product_01.id,
                    "product_qty": 1.0,
                    "orderpoint_id": stock_op.id,
                },
                {
                    "product_id": self.product_01.id,
                    "product_qty": 2.0,
                    "orderpoint_id": sub_op.id,
                },
            ],
        )

        po.action_confirm()
        picking = po.picking_ids
        picking.button_validate()

        self.assertRecordValues(
            picking.move_line_ids,
            [
                {
                    "product_id": self.product_01.id,
                    "quantity": 1.0,
                    "state": "done",
                    "location_dest_id": stock_location.id,
                },
                {
                    "product_id": self.product_01.id,
                    "quantity": 2.0,
                    "state": "done",
                    "location_dest_id": sub_location.id,
                },
            ],
        )

    def test_2steps_and_partner_on_orderpoint(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)]
        )
        route_buy_id = self.ref("purchase_stock.route_warehouse0_buy")

        warehouse.reception_steps = "two_steps"

        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "RR for %s" % self.product_01.name,
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "trigger": "manual",
                "product_id": self.product_01.id,
                "product_min_qty": 1,
                "product_max_qty": 5,
                "route_id": route_buy_id,
                "supplier_id": self.product_01.seller_ids.id,
            }
        )
        orderpoint.action_replenish()

        po_line = self.env["purchase.order.line"].search(
            [
                ("partner_id", "=", self.partner.id),
                ("product_id", "=", self.product_01.id),
            ]
        )
        self.assertEqual(po_line.product_qty, 5)

    def test_change_of_date_planned(self):
        self.env.company.stock_config_id.horizon_days = 0
        delivery_form = Form(self.env["stock.picking"])
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.env.ref("stock.picking_type_out")
        with delivery_form.move_ids.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 1
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery.move_ids.flush_recordset()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()

        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", self.product_01.id)]
        )
        self.assertRecordValues(
            orderpoint,
            [
                {"qty_forecast": -1, "qty_to_order": 1},
            ],
        )

        orderpoint.invalidate_model(fnames=["qty_forecast", "qty_to_order"])
        orderpoint.product_id.invalidate_model(fnames=["qty_available_virtual"])

        delivery.date_planned += td(days=7)
        self.assertRecordValues(
            orderpoint,
            [
                {"qty_forecast": 0, "qty_to_order": 0},
            ],
        )

    def test_decrease_qty_multi_step_receipt(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.reception_steps = "two_steps"
        input_location_id = warehouse.wh_input_stock_loc_id.id
        stock_location_id = warehouse.lot_stock_id.id
        customer_location_id = self.ref("stock.stock_location_customers")
        supplier_location_id = self.ref("stock.stock_location_suppliers")

        self.product_01.description = "Super Note"

        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": self.product_01.name,
                "location_id": stock_location_id,
                "product_id": self.product_01.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
                "trigger": "manual",
            }
        )

        out_move = self.env["stock.move"].create(
            {
                "product_id": self.product_01.id,
                "product_uom_id": self.product_01.uom_id.id,
                "product_uom_qty": 5,
                "location_id": stock_location_id,
                "location_dest_id": customer_location_id,
            }
        )
        out_move._action_confirm()

        op.action_replenish()

        purchase = self.env["purchase.order"].search(
            [("partner_id", "=", self.partner.id)], order="id desc", limit=1
        )
        with Form(purchase) as form:
            with form.line_ids.edit(0) as line:
                line.product_qty = 4
        purchase.action_confirm()
        moves = self.env["stock.move"].search(
            [("id", "!=", out_move.id), ("product_id", "=", self.product_01.id)],
            order="id desc",
        )
        self.assertRecordValues(
            moves,
            [
                {
                    "location_id": supplier_location_id,
                    "location_dest_id": input_location_id,
                    "product_qty": 4,
                },
            ],
        )
        moves.picking_id.button_validate()
        moves = self.env["stock.move"].search(
            [("id", "!=", out_move.id), ("product_id", "=", self.product_01.id)],
            order="id desc",
        )
        self.assertRecordValues(
            moves,
            [
                {
                    "location_id": input_location_id,
                    "location_dest_id": stock_location_id,
                    "product_qty": 4,
                },
                {
                    "location_id": supplier_location_id,
                    "location_dest_id": input_location_id,
                    "product_qty": 4,
                },
            ],
        )

    def test_decrease_qty_multi_step_receipt02(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.reception_steps = "two_steps"
        input_location_id = warehouse.wh_input_stock_loc_id.id
        stock_location_id = warehouse.lot_stock_id.id
        supplier_location_id = self.ref("stock.stock_location_suppliers")

        self.product_01.description = False

        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": self.product_01.name,
                "location_id": stock_location_id,
                "product_id": self.product_01.id,
                "product_min_qty": 4,
                "product_max_qty": 4,
                "trigger": "manual",
            }
        )
        op.action_replenish()

        purchase = self.env["purchase.order"].search(
            [("partner_id", "=", self.partner.id)], order="id desc", limit=1
        )
        with Form(purchase) as form:
            with form.line_ids.edit(0) as line:
                line.product_qty = 10
        purchase.action_confirm()

        moves = self.env["stock.move"].search(
            [("product_id", "=", self.product_01.id)], order="id desc"
        )
        self.assertRecordValues(
            moves,
            [
                {
                    "location_id": supplier_location_id,
                    "location_dest_id": input_location_id,
                    "product_qty": 10,
                },
            ],
        )

        with Form(purchase) as form:
            with form.line_ids.edit(0) as line:
                line.product_qty = 1

        moves = self.env["stock.move"].search(
            [("product_id", "=", self.product_01.id)], order="id desc"
        )
        self.assertRecordValues(
            moves,
            [
                {
                    "location_id": supplier_location_id,
                    "location_dest_id": input_location_id,
                    "product_qty": 1,
                },
            ],
        )

    def test_reordering_rule_horizon_days(self):
        self.env.company.stock_config_id.horizon_days = 4
        wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        op = self.env["stock.warehouse.orderpoint"].create(
            {
                "warehouse_id": wh.id,
                "location_id": wh.lot_stock_id.id,
                "product_id": self.product_01.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )

        move = self.env["stock.move"].create(
            {
                "product_id": self.product_01.id,
                "product_uom_id": self.product_01.uom_id.id,
                "product_uom_qty": 1,
                "location_id": wh.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "date": dt.today() + td(days=6),
            }
        )
        move._action_confirm()
        self.assertEqual(op.qty_to_order, 0, "sale order is ignored")
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_01.id,
                "product_uom_id": self.product_01.uom_id.id,
                "product_uom_qty": 1,
                "location_id": wh.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            }
        )
        move._action_confirm()

        self.product_01.qty_available_virtual = -1
        self.assertEqual(op.qty_to_order, 1, "sale order is ignored")

    def test_reordering_rule_horizon_days_display(self):
        self.env.company.stock_config_id.horizon_days = 3
        today = dt.today()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "product_id": self.product_01.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )

        out_5_days = self.env["stock.move"].create(
            {
                "product_id": self.product_01.id,
                "product_uom_qty": 5,
                "location_id": warehouse.lot_stock_id.id,
                "picking_type_id": warehouse.out_type_id.id,
                "date": today + td(days=5),
            }
        )
        out_5_days._action_confirm()

        replenishment_info = loads(
            self.env["stock.replenishment.info"]
            .create({"orderpoint_id": orderpoint.id})
            .json_lead_days
        )
        self.assertEqual(
            replenishment_info["lead_horizon_date"],
            format_date(orderpoint.env, today + td(days=3) + td(days=1)),
        )
        self.assertEqual(float(replenishment_info["qty_to_order"]), 0)
        context = orderpoint.action_product_forecast_report()["context"]
        self.assertEqual(context["qty_to_order"], 0)
        self.assertEqual(
            context["lead_horizon_date"],
            format_date(orderpoint.env, today + td(days=3) + td(days=1)),
        )

        out_today = self.env["stock.move"].create(
            {
                "product_id": self.product_01.id,
                "product_uom_qty": 3,
                "location_id": warehouse.lot_stock_id.id,
                "picking_type_id": warehouse.out_type_id.id,
                "partner_id": self.partner.id,
                "date": today,
            }
        )
        out_today._action_confirm()

        replenishment_info = loads(
            self.env["stock.replenishment.info"]
            .create({"orderpoint_id": orderpoint.id})
            .json_lead_days
        )
        self.assertEqual(
            replenishment_info["lead_horizon_date"],
            format_date(orderpoint.env, today + td(days=3) + td(days=1)),
        )
        self.assertEqual(float(replenishment_info["qty_to_order"]), 3)
        context = orderpoint.action_product_forecast_report()["context"]
        self.assertEqual(context["qty_to_order"], 3)
        self.assertEqual(
            context["lead_horizon_date"],
            format_date(orderpoint.env, today + td(days=3) + td(days=1)),
        )

    def test_update_po_line_without_purchase_access_right(self):
        user = self.env["res.users"].create(
            {
                "name": "Inventory Manager",
                "login": "inv_manager",
                "group_ids": [(6, 0, [self.env.ref("stock.group_stock_user").id])],
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Storable Product",
                "is_storable": True,
                "seller_ids": [(0, 0, {"partner_id": self.partner.id})],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.env["stock.warehouse.orderpoint"].create(
            {
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "product_id": product.id,
                "product_min_qty": 5,
                "product_max_qty": 5,
            }
        )
        self.env["stock.scheduler"].run()
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertEqual(len(po_line), 1, "There should be only one PO line")
        self.assertEqual(po_line.product_qty, 5, "The PO line quantity should be 5")
        picking = (
            self.env["stock.picking"]
            .with_user(user)
            .create(
                {
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": self.env.ref(
                        "stock.stock_location_customers"
                    ).id,
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
                    "state": "draft",
                }
            )
        )
        picking.with_user(user).action_assign()
        self.assertEqual(po_line.product_qty, 6, "The PO line quantity should be 6")

    def test_set_supplier_in_orderpoint(self):
        product = self.env["product.product"].create(
            {
                "name": "Storable Product",
                "is_storable": True,
                "uom_id": self.env.ref("uom.product_uom_kgm").id,
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.partner.id,
                            "min_qty": 6,
                            "product_uom_id": self.env.ref("uom.product_uom_ton").id,
                        },
                    )
                ],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "product_id": product.id,
                "product_min_qty": 500,
                "product_max_qty": 500,
            }
        )
        product.seller_ids.with_context(
            orderpoint_id=orderpoint.id
        ).action_set_supplier()
        self.assertEqual(
            orderpoint.supplier_id,
            product.seller_ids,
            "The supplier should be set in the orderpoint",
        )
        self.assertEqual(
            orderpoint.product_uom_id,
            product.uom_id,
            "The orderpoint uom should be the same as the product uom",
        )
        self.assertEqual(orderpoint.qty_to_order, 6000)

    def test_tax_po_line_reordering_rule_with_branch_company(self):
        company = self.env.company
        if not company.country_id:
            company.country_id = self.env.ref("base.us")

        self.env.company.write(
            {
                "child_ids": [
                    Command.create(
                        {
                            "name": "Branch A",
                            "country_id": company.country_id.id,
                            "zip": "85120",
                        }
                    )
                ],
            }
        )
        self.cr.precommit.run()
        branch = self.env.company.child_ids

        tax_group = self.env["account.tax.group"].create(
            {
                "name": "Test Tax Group",
                "company_ids": [Command.set(company.ids)],
            }
        )
        purchase_tax = self.env["account.tax"].create(
            {
                "name": "Purchase Tax 10%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 10,
                "tax_group_id": tax_group.id,
                "company_ids": [Command.set(company.ids)],
                "country_id": company.country_id.id,
            }
        )

        buy_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        product = (
            self.env["product.product"]
            .with_company(branch)
            .create(
                {
                    "name": "Storable Product",
                    "is_storable": True,
                    "seller_ids": [
                        Command.create({"partner_id": self.partner.id, "min_qty": 1})
                    ],
                    "supplier_taxes_id": [Command.set([purchase_tax.id])],
                    "route_ids": [Command.set(buy_route.ids)],
                }
            )
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", branch.id)], limit=1
        )
        product.env["stock.warehouse.orderpoint"].create(
            {
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "product_id": product.id,
                "product_min_qty": 10,
                "product_max_qty": 10,
            }
        )
        self.env["stock.scheduler"].run()
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertEqual(len(po_line), 1, "There should be only one PO line")
        self.assertEqual(po_line.product_qty, 10, "The PO line quantity should be 10")
        self.assertTrue(po_line.tax_ids)

    def test_forbid_snoozing_auto_trigger_orderpoint(self):
        buy_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        product = self.env["product.product"].create(
            {
                "name": "Super product",
                "is_storable": True,
                "route_ids": [Command.set(buy_route.ids)],
            }
        )

        with self.assertRaises(UserError):
            orderpoint = self.env["stock.warehouse.orderpoint"].create(
                {
                    "name": "Super product RR",
                    "route_id": buy_route.id,
                    "product_id": product.id,
                    "product_min_qty": 0,
                    "product_max_qty": 5,
                    "snoozed_until": add(Date.today(), days=1),
                }
            )

        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "Super product RR",
                "route_id": buy_route.id,
                "product_id": product.id,
                "product_min_qty": 0,
                "product_max_qty": 5,
            }
        )
        with self.assertRaises(UserError):
            orderpoint.snoozed_until = add(Date.today(), days=1)

    def test_supplierinfo_date_last_purchase(self):
        res_partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Storable Product",
                "is_storable": True,
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "product_min_qty": 0,
                "product_max_qty": 0,
            }
        )
        po1_vals = {
            "partner_id": res_partner.id,
            "date_order": dt.today() - td(days=15),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": product.name,
                        "product_id": product.id,
                        "product_qty": 1.0,
                    },
                )
            ],
        }
        po2_vals = {
            "partner_id": res_partner.id,
            "date_order": dt.today(),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": product.name,
                        "product_id": product.id,
                        "product_qty": 1.0,
                    },
                )
            ],
        }
        po1 = self.env["purchase.order"].create(po1_vals)
        po1.action_confirm()
        po2 = self.env["purchase.order"].create(po2_vals)
        po2.action_confirm()
        replenishment_info = self.env["stock.replenishment.info"].create(
            {"orderpoint_id": orderpoint.id}
        )
        supplier_info = replenishment_info.supplierinfo_ids
        self.assertEqual(
            supplier_info.date_last_purchase,
            dt.today().date(),
            "The last_purhchase_date should be set to the most recent date_order from the purchase orders",
        )

    def test_reordering_rule_multicurrency(self):
        foreign_currency = self.env["res.currency"].create(
            {
                "name": "Coin",
                "symbol": "☺",
            }
        )
        self.env["res.currency.rate"].create(
            {
                "name": "2019-01-01",
                "rate": 0.50,
                "currency_id": foreign_currency.id,
                "company_id": self.env.company.id,
            }
        )

        self.product_01.write(
            {
                "variant_seller_ids": [
                    Command.clear(),
                    Command.create(
                        {
                            "partner_id": self.partner.id,
                            "price": 100,
                            "currency_id": self.env.company.currency_id.id,
                            "product_tmpl_id": self.product_01.product_tmpl_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.partner.id,
                            "price": 10,
                            "currency_id": foreign_currency.id,
                            "product_tmpl_id": self.product_01.product_tmpl_id.id,
                        }
                    ),
                ],
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.user.id)], limit=1
        )

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", self.product_01.id)]
        )
        self.assertFalse(po_line)
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    self.product_01,
                    100,
                    self.product_01.uom_id,
                    warehouse.lot_stock_id,
                    "Test default vendor",
                    "/",
                    self.env.company,
                    {
                        "warehouse_id": warehouse,
                        "date_planned": dt.today() + td(days=1),
                        "rule_id": warehouse.buy_pull_id,
                        "group_id": False,
                        "route_ids": [],
                    },
                )
            ]
        )
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", self.product_01.id)]
        )
        self.assertTrue(po_line)
        self.assertEqual(po_line.order_id.currency_id, foreign_currency)

    def test_intercompany_reordering_rules(self):
        company_a, company_b = self.env["res.company"].create(
            [
                {"name": "Company A"},
                {"name": "Company B"},
            ]
        )
        warehouse_a, warehouse_b = (
            self.env["stock.warehouse"]
            .search([("company_id", "in", [company_a.id, company_b.id])], limit=2)
            .sorted("company_id")
        )
        route_resupply_from_intercomp = self.env["stock.route"].create(
            [
                {
                    "name": "ressuply from intercomp",
                    "active": True,
                    "company_id": False,
                    "product_selectable": True,
                    "rule_ids": [
                        Command.create(
                            {
                                "name": "inter-comp -> Stock A",
                                "action": "pull",
                                "picking_type_id": warehouse_a.int_type_id.id,
                                "location_src_id": self.ref(
                                    "stock.stock_location_inter_company"
                                ),
                                "location_dest_id": warehouse_a.lot_stock_id.id,
                                "company_id": company_a.id,
                                "procure_method": "make_to_order",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Stock B -> inter-comp",
                                "action": "buy",
                                "picking_type_id": warehouse_b.out_type_id.id,
                                "location_src_id": warehouse_b.lot_stock_id.id,
                                "location_dest_id": self.ref(
                                    "stock.stock_location_inter_company"
                                ),
                                "company_id": company_b.id,
                                "procure_method": "make_to_order",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Buy -> Stock B",
                                "action": "buy",
                                "picking_type_id": warehouse_b.in_type_id.id,
                                "location_dest_id": warehouse_b.lot_stock_id.id,
                                "company_id": company_b.id,
                                "procure_method": "make_to_stock",
                            }
                        ),
                    ],
                },
            ]
        )
        product = self.env["product.product"].create(
            {
                "name": "super product",
                "is_storable": True,
                "route_ids": [Command.set(route_resupply_from_intercomp.ids)],
                "seller_ids": [
                    Command.create(
                        {"partner_id": self.partner.id, "company_id": company_b.id}
                    )
                ],
            }
        )
        orderpoint = (
            self.env["stock.warehouse.orderpoint"]
            .with_company(company_a)
            .create(
                {
                    "name": "RR for %s" % product.name,
                    "warehouse_id": warehouse_a.id,
                    "location_id": warehouse_a.lot_stock_id.id,
                    "trigger": "manual",
                    "product_id": product.id,
                    "product_min_qty": 10,
                    "product_max_qty": 10,
                    "route_id": route_resupply_from_intercomp.id,
                }
            )
        )
        orderpoint.action_replenish()
        self.assertRecordValues(
            self.env["purchase.order"]
            .search(
                [
                    ("company_id", "=", company_b.id),
                    ("partner_id", "=", self.partner.id),
                ],
                limit=1,
            )
            .line_ids,
            [
                {
                    "product_id": product.id,
                    "product_uom_qty": 10,
                }
            ],
        )

    def test_backorder_mto_buy(self):
        buy_product = self.product_01
        mto_route = self.env.ref("stock.route_warehouse0_mto")
        mto_route.active = True
        buy_product.route_ids |= mto_route
        reference = self.env["stock.reference"].create(
            {"name": "test_backorder_mto_buy"}
        )
        self.env["stock.rule"].run(
            [
                self.env["stock.rule"].Procurement(
                    buy_product,
                    100,
                    buy_product.uom_id,
                    self.env.ref("stock.stock_location_customers"),
                    "Test mto buy",
                    "/",
                    self.env.company,
                    {
                        "warehouse_id": self.env.ref("stock.warehouse0"),
                        "reference_ids": reference,
                    },
                )
            ]
        )
        po_line = reference.purchase_ids.line_ids
        self.assertEqual(po_line.product_uom_qty, 100)
        delivery = po_line.move_dest_ids.picking_id
        delivery.move_ids.quantity = 30
        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process()
        purchase_order_line = self.env["purchase.order.line"].search(
            [("product_id", "=", buy_product.id)]
        )
        self.assertRecordValues(
            delivery.backorder_ids.move_ids,
            [
                {
                    "product_uom_qty": 70,
                    "procure_method": "make_to_order",
                    "state": "waiting",
                    "created_purchase_line_ids": purchase_order_line.ids,
                }
            ],
        )
        self.assertEqual(delivery.backorder_ids.reference_ids, delivery.reference_ids)
        self.assertRecordValues(
            purchase_order_line,
            [
                {
                    "product_uom_qty": 100,
                    "move_dest_ids": [
                        delivery.move_ids.id,
                        delivery.backorder_ids.move_ids.id,
                    ],
                }
            ],
        )

    def test_orderpoint_warning_purchase_stock(self):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.product_01.id,
                "product_min_qty": 10,
                "product_max_qty": 50,
            }
        )
        self.assertFalse(orderpoint.show_supply_warning)

        self.product_01.seller_ids = False
        orderpoint.invalidate_recordset(fnames=["show_supply_warning"])
        self.assertTrue(orderpoint.show_supply_warning)

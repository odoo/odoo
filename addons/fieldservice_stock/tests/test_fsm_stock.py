# Copyright (C) 2020, Brian McMaster
# Copyright (C) 2021 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestFSMStockCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.location = self.env["fsm.location"]
        self.FSMOrder = self.env["fsm.order"]
        self.Product = self.env["product.product"].search([], limit=1)
        self.stock_cust_loc = self.env.ref("stock.stock_location_customers")
        self.stock_location = self.env.ref("stock.stock_location_stock")
        self.customer_location = self.env.ref("stock.stock_location_customers")
        self.test_location = self.env.ref("fieldservice.test_location")
        self.partner_1 = (
            self.env["res.partner"]
            .with_context(tracking_disable=True)
            .create({"name": "Partner 1"})
        )
        self.customer = self.env["res.partner"].create({"name": "SuperPartner"})

    def test_fsm_orders(self):
        """Test creating new workorders, and test following functions."""
        # Create an Orders
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        hours_diff = 100
        pick_list = []
        order_in_pickings = []
        order_pick_list2 = []
        date_start = fields.Datetime.today()
        order = self.FSMOrder.create(
            {
                "location_id": self.test_location.id,
                "date_start": date_start,
                "date_end": date_start + timedelta(hours=hours_diff),
                "request_early": fields.Datetime.today(),
            }
        )
        order2 = self.FSMOrder.create(
            {
                "location_id": self.test_location.id,
                "date_start": date_start,
                "date_end": date_start + timedelta(hours=50),
                "request_early": fields.Datetime.today(),
            }
        )
        order3 = self.FSMOrder.create(
            {
                "location_id": self.test_location.id,
                "date_start": date_start,
                "date_end": date_start + timedelta(hours=50),
                "request_early": fields.Datetime.today(),
            }
        )
        self.picking = self.env["stock.picking"].create(
            {
                "location_dest_id": self.stock_location.id,
                "location_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "fsm_order_id": order3.id,
            }
        )
        self.picking1 = self.env["stock.picking"].create(
            {
                "location_dest_id": self.stock_location.id,
                "location_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "fsm_order_id": order3.id,
            }
        )
        order_in_pickings.append(self.picking.id)
        order_in_pickings.append(self.picking1.id)
        self.in_picking = self.env["stock.picking"].create(
            {
                "location_dest_id": self.stock_location.id,
                "location_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "fsm_order_id": order.id,
            }
        )
        order_pick_list2.append(self.in_picking.id)
        self.out_picking = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
            }
        )
        order_pick_list2.append(self.out_picking.id)
        self.out_picking2 = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "fsm_order_id": order2.id,
            }
        )
        pick_list.append(self.out_picking2.id)
        self.out_picking3 = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "partner_id": self.customer.id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "fsm_order_id": order2.id,
            }
        )
        rule = self.env["stock.rule"].create(
            {
                "name": "Rule Supplier",
                "route_id": warehouse.reception_route_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "location_src_id": self.env.ref("stock.stock_location_suppliers").id,
                "action": "pull",
                "delay": 9.0,
                "procure_method": "make_to_stock",
                "picking_type_id": warehouse.in_type_id.id,
            }
        )
        rule._get_stock_move_values(
            self.Product,
            1,
            self.Product.uom_id,
            warehouse.lot_stock_id,
            "name",
            "origin",
            self.env.user.company_id,
            {"date_planned": fields.Datetime.today()},
        )
        pick_list.append(self.out_picking3.id)
        order2.picking_ids = [(6, 0, pick_list)]
        order3.picking_ids = [(6, 0, order_in_pickings)]
        order.picking_ids = [(6, 0, order_pick_list2)]
        order._compute_picking_ids()
        order.location_id._onchange_fsm_parent_id()
        order._default_warehouse_id()
        order.action_view_delivery()
        order2.action_view_delivery()
        order3.action_view_returns()
        order.action_view_returns()

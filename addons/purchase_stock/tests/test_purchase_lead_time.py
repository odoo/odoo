from datetime import datetime, time, timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import Form, freeze_time

from .common import PurchaseTestCommon


class TestPurchaseLeadTime(PurchaseTestCommon):
    def test_00_product_company_level_delays(self):
        self._use_route_buy(self.product)
        date_planned = fields.Datetime.now() + timedelta(days=10)
        self._make_procurement(self.product, 15.00, date_planned=date_planned)
        purchase = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product.id)], limit=1)
            .order_id
        )

        purchase.action_confirm()

        order_date = fields.Datetime.from_string(date_planned) - timedelta(
            days=self.product.seller_ids.delay
        )
        self.assertEqual(
            purchase.date_order,
            order_date,
            "Order date should be equal to: Date of the procurement order - Purchase Lead Time - Delivery Lead Time.",
        )

        schedule_date = order_date + timedelta(days=self.product.seller_ids.delay)
        self.assertEqual(
            purchase.line_ids.date_commitment,
            schedule_date,
            "Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time.",
        )

        self.assertTrue(purchase.picking_ids, "Picking should be created.")

        self.assertEqual(
            purchase.picking_ids.date_planned,
            schedule_date,
            "Schedule date of In type shipment should be equal to: schedule date of purchase order.",
        )
        self.assertEqual(
            purchase.picking_ids.date_deadline,
            schedule_date,
            "Deadline date of should be equal to: schedule date of purchase order.",
        )

    def test_01_product_level_delay(self):
        self._use_route_buy(self.product)
        self.product_2 = self.product.copy()
        self._use_route_buy(self.product_2)
        date_planned1 = fields.Datetime.now() + timedelta(days=5)
        self._make_procurement(self.product, 10.00, date_planned=date_planned1)
        purchase1 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product.id)], limit=1)
            .order_id
        )

        date_planned2 = fields.Datetime.now() + timedelta(days=10)
        self._make_procurement(self.product_2, 5.00, date_planned=date_planned2)
        purchase2 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_2.id)], limit=1)
            .order_id
        )

        self.assertEqual(
            purchase1,
            purchase2,
            "Purchase orders should be same for the two different product with same vendor.",
        )

        purchase1.action_confirm()

        order_line_pro_1 = purchase2.line_ids.filtered(
            lambda r: r.product_id == self.product
        )
        order_line_pro_2 = purchase2.line_ids.filtered(
            lambda r: r.product_id == self.product_2
        )
        order_date = date_planned1 - timedelta(days=self.product.seller_ids.delay)
        self.assertEqual(
            purchase2.date_order,
            order_date,
            "Order date should be equal to: Date of the procurement order - Delivery Lead Time.",
        )

        self.assertEqual(
            order_line_pro_1.date_commitment,
            date_planned1,
            "Schedule date of purchase order line for product_1 should be equal to: Order date of purchase order + Delivery Lead Time of product_1.",
        )

        self.assertEqual(
            order_line_pro_2.date_commitment,
            date_planned2,
            "Schedule date of purchase order line for product_2 should be equal to: Order date of purchase order + Delivery Lead Time of product_2.",
        )

        self.assertTrue(purchase2.picking_ids, "Picking should be created.")

        picking_schedule_date = min(date_planned1, date_planned2)
        self.assertEqual(
            purchase2.picking_ids.date_planned,
            picking_schedule_date,
            "Schedule date of In type shipment should be same as schedule date of purchase order.",
        )

        self.assertEqual(
            fields.Date.to_date(purchase2.picking_ids.date_deadline),
            fields.Date.to_date(purchase1.date_commitment),
            "Deadline of pickings should be equals to the receipt date of purchase",
        )
        purchase_form = Form(purchase2)
        purchase_form.date_commitment = purchase2.date_commitment + timedelta(days=2)
        purchase_form.save()
        self.assertEqual(
            purchase2.picking_ids.date_deadline,
            purchase2.date_commitment,
            "Deadline of pickings should be propagate",
        )

    def test_02_product_level_delay(self):
        self._use_route_buy(self.product)
        self.product_2 = self.product.copy()
        self._use_route_buy(self.product_2)

        self.vendor.group_rfq = "day"
        date_planned = fields.Datetime.now()
        ref1, ref2 = self.env["stock.reference"].create(
            [
                {"name": "SO001"},
                {"name": "SO002"},
            ]
        )
        self._make_procurement(
            self.product,
            10.00,
            date_planned=date_planned,
            procurement_values={"reference_ids": ref1},
        )
        purchase1 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product.id)], limit=1)
            .order_id
        )

        self._make_procurement(
            self.product_2,
            5.00,
            date_planned=date_planned,
            procurement_values={"reference_ids": ref2},
        )
        purchase2 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_2.id)], limit=1)
            .order_id
        )

        self.assertEqual(
            purchase1,
            purchase2,
            "Purchase orders should be same for the two different product with same vendor.",
        )

        purchase1.action_confirm()

        order_line_pro_1 = purchase1.line_ids.filtered(
            lambda r: r.product_id == self.product
        )
        order_line_pro_2 = purchase2.line_ids.filtered(
            lambda r: r.product_id == self.product_2
        )
        self.assertEqual(
            purchase2.date_commitment,
            date_planned,
            "planned date should be equal to procurement date",
        )
        deadline = date_planned - timedelta(
            days=max((self.product | self.product_2).seller_ids.mapped("delay"))
        )
        self.assertEqual(
            purchase2.date_order,
            deadline,
            "Deadline date should be equal to: Date of the procurement order - max Lead Time.",
        )

        self.assertEqual(
            order_line_pro_1.date_commitment,
            date_planned,
            "Schedule date of purchase order line for product_1 should be equal to: Order date of purchase order + Delivery Lead Time of product_1.",
        )

        self.assertEqual(
            order_line_pro_2.date_commitment,
            date_planned,
            "Schedule date of purchase order line for product_2 should be equal to: Order date of purchase order + Delivery Lead Time of product_2.",
        )

    @freeze_time("2025-09-10 10:00:00")
    def test_03_group_week(self):
        self._use_route_buy(self.product)
        self.product.seller_ids.delay = 0
        self.product_2 = self.product.copy()
        self._use_route_buy(self.product_2)
        self.product_2.seller_ids.delay = 2
        self.vendor.group_rfq = "week"
        self.vendor.group_on = "2"
        date_planned = fields.Datetime.now() + timedelta(days=2)
        ref1, ref2 = self.env["stock.reference"].create(
            [
                {"name": "SO001"},
                {"name": "SO002"},
            ]
        )
        self._make_procurement(
            self.product,
            10.00,
            date_planned=date_planned,
            procurement_values={"reference_ids": ref1},
        )
        purchase1 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product.id)], limit=1)
            .order_id
        )

        date_planned = fields.Datetime.now() + timedelta(days=3)
        self._make_procurement(
            self.product_2,
            5.00,
            date_planned=date_planned,
            procurement_values={"reference_ids": ref2},
        )
        purchase2 = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.product_2.id)], limit=1)
            .order_id
        )

        self.assertEqual(
            purchase1,
            purchase2,
            "Purchase orders should be same for the two different product with same vendor.",
        )

        purchase1.action_confirm()

        date_p = fields.Datetime.from_string("2025-09-16 10:00:00")
        date_d = fields.Datetime.from_string("2025-09-14 10:00:00")
        self.assertRecordValues(
            purchase1,
            [
                {
                    "date_commitment": date_p,
                    "date_order": date_d,
                }
            ],
        )
        self.assertRecordValues(
            purchase1.line_ids,
            [
                {"date_commitment": date_p},
                {"date_commitment": date_p},
            ],
        )

    def test_merge_po_line(self):
        product_1 = self.env["product.product"].create(
            {
                "name": "AAA",
                "route_ids": [Command.link(self.route_buy.id)],
                "seller_ids": [
                    Command.create({"partner_id": self.partner.id, "delay": 5})
                ],
            }
        )

        move_1 = self.env["stock.move"].create(
            {
                "product_id": product_1.id,
                "product_uom_id": self.uom.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.warehouse.wh_output_stock_loc_id.id,
                "product_uom_qty": 10,
                "procure_method": "make_to_order",
            }
        )

        move_1._action_confirm()
        po_line = self.env["purchase.order.line"].search(
            [
                ("product_id", "=", product_1.id),
            ]
        )
        self.assertEqual(len(po_line), 1, "the purchase order line is not created")
        self.assertEqual(
            po_line.product_qty, 10, "the purchase order line has a wrong quantity"
        )

        move_2 = self.env["stock.move"].create(
            {
                "product_id": product_1.id,
                "product_uom_id": self.uom.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.warehouse.wh_output_stock_loc_id.id,
                "product_uom_qty": 5,
                "procure_method": "make_to_order",
            }
        )

        move_2._action_confirm()
        po_line = self.env["purchase.order.line"].search(
            [
                ("product_id", "=", product_1.id),
            ]
        )
        self.assertEqual(len(po_line), 1, "the purchase order lines should be merged")
        self.assertEqual(
            po_line.product_qty, 15, "the purchase order line has a wrong quantity"
        )

    def test_merge_po_line_3(self):
        self.t_shirt = self.env["product.product"].create(
            {
                "name": "T-shirt",
                "description": "Internal Notes",
            }
        )
        self._use_route_buy(self.t_shirt)
        self.t_shirt.seller_ids.write(
            {
                "delay": 5,
                "product_name": "Vendor Name",
                "product_code": "Vendor Code",
            }
        )
        partner = self.t_shirt.seller_ids[:1].partner_id
        t_shirt = self.t_shirt.with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )
        t_shirt.description_pickingin = "Receive with care"

        StockRule = self.env["stock.rule"]
        procurement_values = {
            "warehouse_id": self.warehouse,
            "rule_id": self.warehouse.buy_pull_id,
            "date_planned": fields.Datetime.now() + timedelta(days=10),
            "group_id": False,
            "route_ids": [],
        }

        procurement_values["product_description_variants"] = "Color (Red)"
        order_1_values = procurement_values
        StockRule.run(
            [
                self.env["stock.rule"].Procurement(
                    self.t_shirt,
                    5,
                    self.uom,
                    self.warehouse.lot_stock_id,
                    self.t_shirt.name,
                    "/",
                    self.env.company,
                    order_1_values,
                )
            ]
        )
        purchase_order = (
            self.env["purchase.order.line"]
            .search([("product_id", "=", self.t_shirt.id)], limit=1)
            .order_id
        )
        self.assertEqual(
            len(purchase_order.line_ids), 1, "wrong number of order line is created"
        )
        self.assertEqual(
            purchase_order.line_ids.name,
            t_shirt.display_name + "\n" + "Color (Red)",
            "wrong description in po lines",
        )

        procurement_values["product_description_variants"] = "Color (Red)"
        order_2_values = procurement_values
        StockRule.run(
            [
                self.env["stock.rule"].Procurement(
                    self.t_shirt,
                    10,
                    self.uom,
                    self.warehouse.lot_stock_id,
                    self.t_shirt.name,
                    "/",
                    self.env.company,
                    order_2_values,
                )
            ]
        )
        self.env["stock.scheduler"].run()
        self.assertEqual(
            len(purchase_order.line_ids),
            1,
            "line with same custom value should be merged",
        )
        self.assertEqual(
            purchase_order.line_ids[0].product_qty,
            15,
            "line with same custom value should be merged and qty should be update",
        )

        procurement_values["product_description_variants"] = "Color (Green)"

        order_3_values = procurement_values
        StockRule.run(
            [
                self.env["stock.rule"].Procurement(
                    self.t_shirt,
                    10,
                    self.uom,
                    self.warehouse.lot_stock_id,
                    self.t_shirt.name,
                    "/",
                    self.env.company,
                    order_3_values,
                )
            ]
        )
        self.assertEqual(
            len(purchase_order.line_ids),
            2,
            "line with different custom value should not be merged",
        )
        self.assertEqual(
            purchase_order.line_ids.filtered(lambda x: x.product_qty == 15).name,
            t_shirt.display_name + "\n" + "Color (Red)",
            "wrong description in po lines",
        )
        self.assertEqual(
            purchase_order.line_ids.filtered(lambda x: x.product_qty == 10).name,
            t_shirt.display_name + "\n" + "Color (Green)",
            "wrong description in po lines",
        )

        purchase_order.action_confirm()
        self.assertEqual(
            purchase_order.picking_ids[0]
            .move_ids.filtered(lambda x: x.product_uom_qty == 15)
            .description_picking,
            t_shirt.display_name + "\n" + "Receive with care",
            "wrong description in picking",
        )
        self.assertEqual(
            purchase_order.picking_ids[0]
            .move_ids.filtered(lambda x: x.product_uom_qty == 10)
            .description_picking,
            t_shirt.display_name + "\n" + "Receive with care",
            "wrong description in picking",
        )

    def test_reordering_days_to_purchase(self):
        self.company.stock_config_id.horizon_days = 0
        self.patcher = patch(
            "odoo.addons.stock.models.stock_orderpoint.fields.Date", wraps=fields.Date
        )
        self.mock_date = self.startPatcher(self.patcher)

        vendor = self.env["res.partner"].create({"name": "Colruyt"})
        vendor2 = self.env["res.partner"].create({"name": "Delhaize"})

        self.company.purchase_config_id.days_to_purchase = 2.0

        prod = self.env["product.product"].create(
            {
                "name": "Carrot",
                "is_storable": True,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": vendor.id,
                            "delay": 1.0,
                            "company_id": self.company.id,
                        }
                    )
                ],
            }
        )

        self.env["stock.move"].create(
            {
                "date": datetime.today() + timedelta(days=3),
                "product_id": prod.id,
                "product_uom_id": prod.uom_id.id,
                "product_uom_qty": 5.0,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )._action_confirm()
        self.env["stock.warehouse.orderpoint"].action_view_orderpoints()
        replenishment = self.env["stock.warehouse.orderpoint"].search(
            [
                ("product_id", "=", prod.id),
            ]
        )
        self.assertEqual(len(replenishment), 1)

        product = self.env["product.product"].create(
            {
                "name": "Chicory",
                "is_storable": True,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": vendor2.id,
                            "delay": 15.0,
                            "company_id": self.other_company.id,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": vendor.id,
                            "delay": 1.0,
                            "company_id": self.company.id,
                        }
                    ),
                ],
            }
        )
        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.0
        self.company.stock_config_id.horizon_days = 1
        orderpoint_form.save()

        orderpoint_form = Form(
            self.env["stock.warehouse.orderpoint"].with_company(self.other_company)
        )
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.save()

        delivery_moves = self.env["stock.move"]
        for i in range(6):
            delivery_moves |= self.env["stock.move"].create(
                {
                    "date": datetime.today() + timedelta(days=i),
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "product_uom_qty": 5.0,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                }
            )
        delivery_moves._action_confirm()

        self.env["stock.scheduler"].run()
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        expected_date_order = fields.Date.today() + timedelta(days=2)
        self.assertEqual(
            fields.Date.to_date(po_line.order_id.date_order), expected_date_order
        )
        self.assertEqual(len(po_line), 1)
        self.assertEqual(po_line.product_uom_qty, 25.0)
        self.assertEqual(len(po_line.order_id), 1)

        self.mock_date.today.return_value = fields.Date.today() + timedelta(days=2)
        self.env.invalidate_all()
        self.env["stock.scheduler"].run()
        po_line02 = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)]
        )
        self.assertEqual(
            po_line02, po_line, "The orderpoint execution should not create a new POL"
        )
        self.assertEqual(
            fields.Date.to_date(po_line.order_id.date_order),
            expected_date_order,
            "The Order Deadline should not change",
        )
        self.assertEqual(
            po_line.product_uom_qty,
            30.0,
            "The existing POL should be updated with the quantity of the last execution",
        )

    def test_supplier_lead_time(self):
        self.env["stock.warehouse.orderpoint"].search([]).unlink()
        orderpoint_form = Form(self.env["stock.warehouse.orderpoint"])
        orderpoint_form.product_id = self.product
        orderpoint_form.product_min_qty = 10
        orderpoint_form.product_max_qty = 50
        orderpoint_form.save()

        self.env["product.supplierinfo"].search(
            [("product_tmpl_id", "=", self.product.product_tmpl_id.id)]
        ).unlink()
        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.partner.id,
                "min_qty": 1,
                "price": 1,
                "delay": 7,
                "product_tmpl_id": self.product.product_tmpl_id.id,
            }
        )

        self.env["stock.scheduler"].run()
        purchase_order = self.env["purchase.order"].search(
            [("partner_id", "=", self.partner.id)]
        )

        today = datetime.combine(fields.Datetime.now(), time(12))
        self.assertEqual(purchase_order.date_order, today)
        self.assertEqual(purchase_order.date_commitment, today + timedelta(days=7))

    def test_lead_time_with_no_supplier(self):
        self._use_route_buy(self.product, create_seller=False)
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "test",
                "location_id": self.stock_location.id,
                "product_id": self.product.id,
                "product_min_qty": 0,
                "product_max_qty": 5,
            }
        )

        self.assertEqual(orderpoint.lead_days, 365)

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import Form

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.stock.tests.common import TestStockCommon


class TestStockLot(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.apple_product = cls.ProductObj.create(
            {
                "name": "Apple",
                "is_storable": True,
                "tracking": "lot",
                "use_expiration_date": True,
                "expiration_time": 10,
                "use_time": 5,
                "removal_time": 2,
                "alert_time": 6,
            }
        )

    def test_00_stock_production_lot(self):

        self.productAAA = self.ProductObj.create(
            {
                "name": "Product AAA",
                "is_storable": True,
                "tracking": "lot",
                "company_id": self.env.company.id,
            }
        )

        self.lot1_productAAA = self.LotObj.create(
            {
                "name": "Lot 1 ProductAAA",
                "product_id": self.productAAA.id,
                "alert_date": fields.Date.to_string(
                    datetime.today() - relativedelta(days=15)
                ),
            }
        )

        picking_in = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "state": "draft",
            }
        )

        move_a = self.MoveObj.create(
            {
                "product_id": self.productAAA.id,
                "product_uom_qty": 33,
                "product_uom_id": self.productAAA.uom_id.id,
                "picking_id": picking_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )

        self.assertEqual(
            picking_in.move_ids.state, "draft", "Wrong state of move line."
        )
        picking_in.action_confirm()
        self.assertEqual(
            picking_in.move_ids.state, "assigned", "Wrong state of move line."
        )

        picking_in.action_assign()
        move_a.move_line_ids.quantity = 33
        move_a.move_line_ids.lot_id = self.lot1_productAAA.id

        move_a.picked = True
        picking_in._action_done()

        self.env["stock.lot"]._alert_lots_past_alert_date()

        activity_id = self.env.ref("mail.mail_activity_data_todo").id
        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productAAA.id),
            ]
        )
        self.assertEqual(
            activity_count, 1, "No activity created while there should be one"
        )

        self.env["stock.lot"]._alert_lots_past_alert_date()

        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productAAA.id),
            ]
        )
        self.assertEqual(activity_count, 1, "There should be one and only one activity")

        mail_activity = self.env["mail.activity"].search(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productAAA.id),
            ]
        )
        mail_activity.action_done()

        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productAAA.id),
            ]
        )
        self.assertEqual(
            activity_count,
            0,
            "As activity is done, there shouldn't be any related activity",
        )

        self.env["stock.lot"]._alert_lots_past_alert_date()

        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productAAA.id),
            ]
        )
        self.assertEqual(
            activity_count,
            0,
            "As there is already an activity marked as done, there shouldn't be any related activity created for this lot",
        )

    def test_01_stock_production_lot(self):

        self.productBBB = self.ProductObj.create(
            {"name": "Product BBB", "is_storable": True, "tracking": "lot"}
        )

        self.lot1_productBBB = self.LotObj.create(
            {
                "name": "Lot 1 ProductBBB",
                "product_id": self.productBBB.id,
                "alert_date": fields.Date.to_string(
                    datetime.today() + relativedelta(days=15)
                ),
            }
        )

        picking_in = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "state": "draft",
                "location_dest_id": self.stock_location.id,
            }
        )

        move_b = self.MoveObj.create(
            {
                "product_id": self.productBBB.id,
                "product_uom_qty": 44,
                "product_uom_id": self.productBBB.uom_id.id,
                "picking_id": picking_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )

        self.assertEqual(
            picking_in.move_ids.state, "draft", "Wrong state of move line."
        )
        picking_in.action_confirm()
        self.assertEqual(
            picking_in.move_ids.state, "assigned", "Wrong state of move line."
        )

        picking_in.action_assign()
        move_b.move_line_ids.quantity = 44
        move_b.move_line_ids.lot_id = self.lot1_productBBB.id

        picking_in._action_done()

        self.env["stock.lot"]._alert_lots_past_alert_date()

        activity_id = self.env.ref("mail.mail_activity_data_todo").id
        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productBBB.id),
            ]
        )
        self.assertEqual(
            activity_count, 0, "An activity has been created while it shouldn't"
        )

    def test_02_stock_production_lot(self):

        self.productCCC = self.ProductObj.create(
            {"name": "Product CCC", "is_storable": True, "tracking": "lot"}
        )

        self.lot1_productCCC = self.LotObj.create(
            {"name": "Lot 1 ProductCCC", "product_id": self.productCCC.id}
        )

        picking_in = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "state": "draft",
                "location_dest_id": self.stock_location.id,
            }
        )

        move_c = self.MoveObj.create(
            {
                "product_id": self.productCCC.id,
                "product_uom_qty": 44,
                "product_uom_id": self.productCCC.uom_id.id,
                "picking_id": picking_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )

        self.assertEqual(
            picking_in.move_ids.state, "draft", "Wrong state of move line."
        )
        picking_in.action_confirm()
        self.assertEqual(
            picking_in.move_ids.state, "assigned", "Wrong state of move line."
        )

        picking_in.action_assign()
        move_c.move_line_ids.quantity = 55
        move_c.move_line_ids.lot_id = self.lot1_productCCC.id

        picking_in._action_done()

        self.env["stock.lot"]._alert_lots_past_alert_date()

        activity_id = self.env.ref("mail.mail_activity_data_todo").id
        activity_count = self.env["mail.activity"].search_count(
            [
                ("activity_type_id", "=", activity_id),
                ("res_model_id", "=", self.env.ref("stock.model_stock_lot").id),
                ("res_id", "=", self.lot1_productCCC.id),
            ]
        )
        self.assertEqual(
            activity_count, 0, "An activity has been created while it shouldn't"
        )

    def test_03_onchange_expiration_date(self):

        def check_expiration_dates(product, lot, start_date, delta):
            self.assertAlmostEqual(
                start_date + timedelta(days=product.expiration_time),
                lot.expiration_date,
                delta=delta,
            )
            self.assertAlmostEqual(
                lot.expiration_date - timedelta(days=product.use_time),
                lot.use_date,
                delta=delta,
            )
            self.assertAlmostEqual(
                lot.expiration_date - timedelta(days=product.removal_time),
                lot.removal_date,
                delta=delta,
            )
            self.assertAlmostEqual(
                lot.expiration_date - timedelta(days=product.alert_time),
                lot.alert_date,
                delta=delta,
            )

        today_date = datetime.today()
        time_gap = timedelta(seconds=10)
        lot_form = Form(self.LotObj)
        lot_form.name = "Apple Box #1"
        lot_form.product_id = self.apple_product
        apple_lot = lot_form.save()
        check_expiration_dates(self.apple_product, apple_lot, today_date, time_gap)

        difference = timedelta(days=20)
        new_expiration_date = apple_lot.expiration_date + difference
        new_start_date = new_expiration_date - timedelta(
            days=self.apple_product.expiration_time
        )
        random_date = new_expiration_date + difference

        lot_form = Form(apple_lot)
        lot_form.expiration_date = new_expiration_date
        lot_form.expiration_date = random_date
        lot_form.expiration_date = new_expiration_date
        apple_lot = lot_form.save()

        check_expiration_dates(self.apple_product, apple_lot, new_start_date, time_gap)

        lot_form = Form(apple_lot)
        lot_form.expiration_date = False
        lot_form.use_date = False
        lot_form.removal_date = False
        lot_form.alert_date = False
        lot_form.save()
        lot_form.expiration_date = random_date
        lot_form.expiration_date = new_expiration_date
        apple_lot = lot_form.save()

        check_expiration_dates(self.apple_product, apple_lot, new_start_date, time_gap)

    def test_04_expiration_date_on_receipt(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Apple's Joe",
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        expiration_date = datetime.today() + timedelta(days=30)
        time_gap = timedelta(seconds=10)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        receipt = picking_form.save()
        receipt.action_confirm()

        move_form = Form(receipt.move_ids, view="stock.view_stock_move_form_operations")
        with move_form.move_line_ids.edit(0) as line:
            line.lot_name = "Apple Box #2"
            line.expiration_date = expiration_date
        move = move_form.save()

        move.picked = True
        receipt._action_done()
        apple_lot = self.env["stock.lot"].search(
            [("product_id", "=", self.apple_product.id)],
            limit=1,
        )
        self.assertAlmostEqual(
            apple_lot.expiration_date, expiration_date, delta=time_gap
        )
        self.assertAlmostEqual(
            apple_lot.use_date,
            expiration_date - timedelta(days=self.apple_product.use_time),
            delta=time_gap,
        )
        self.assertAlmostEqual(
            apple_lot.removal_date,
            expiration_date - timedelta(days=self.apple_product.removal_time),
            delta=time_gap,
        )
        self.assertAlmostEqual(
            apple_lot.alert_date,
            expiration_date - timedelta(days=self.apple_product.alert_time),
            delta=time_gap,
        )

    def test_04_2_expiration_date_on_receipt(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Apple's Joe",
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        self.apple_product.expiration_time = False
        self.apple_product.removal_time = False

        expiration_date = datetime.today() + timedelta(days=30)
        time_gap = timedelta(seconds=10)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.quantity = 4
            move.picked = True
        receipt = picking_form.save()

        move = receipt.move_ids[0]
        line = move.move_line_ids[0]
        self.assertEqual(move.use_expiration_date, True)
        line.lot_name = "Apple Box #3"
        line.expiration_date = expiration_date

        receipt._action_done()
        apple_lot = self.env["stock.lot"].search(
            [("product_id", "=", self.apple_product.id)],
            limit=1,
        )
        self.assertAlmostEqual(
            apple_lot.expiration_date,
            expiration_date,
            delta=time_gap,
            msg="Must be define even if the product's `expiration_time` isn't set.",
        )
        self.assertAlmostEqual(
            apple_lot.use_date,
            expiration_date - timedelta(days=self.apple_product.use_time),
            delta=time_gap,
        )
        self.assertEqual(
            apple_lot.removal_date,
            expiration_date,
            "Must same as expiration_date as the `removal_time` isn't set on product.",
        )
        self.assertAlmostEqual(
            apple_lot.alert_date,
            expiration_date - timedelta(days=self.apple_product.alert_time),
            delta=time_gap,
        )

    def test_05_confirmation_on_delivery(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Cider & Son",
                "company_id": self.env.ref("base.main_company").id,
            }
        )
        lot_form = Form(self.LotObj)
        lot_form.name = "good-apple-lot"
        lot_form.product_id = self.apple_product
        good_lot = lot_form.save()

        lot_form = Form(self.LotObj)
        lot_form.name = "expired-apple-lot-01"
        lot_form.product_id = self.apple_product
        expired_lot_1 = lot_form.save()
        lot_form = Form(expired_lot_1)
        lot_form.expiration_date = datetime.today() - timedelta(days=10)
        expired_lot_1 = lot_form.save()

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        delivery_1 = picking_form.save()
        delivery_1.action_confirm()
        delivery_1.move_line_ids = [
            (5, 0),
            (
                0,
                0,
                {
                    "company_id": self.env.company.id,
                    "location_id": delivery_1.move_ids.location_id.id,
                    "location_dest_id": delivery_1.move_ids.location_dest_id.id,
                    "lot_id": good_lot.id,
                    "product_id": self.apple_product.id,
                    "product_uom_id": self.apple_product.uom_id.id,
                    "quantity": 4,
                },
            ),
        ]
        delivery_1.move_ids.picked = True
        res = delivery_1.button_validate()
        self.assertEqual(res, True)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 8
        delivery_2 = picking_form.save()
        delivery_2.action_confirm()
        delivery_2.move_line_ids = [
            (5, 0),
            (
                0,
                0,
                {
                    "company_id": self.env.company.id,
                    "location_id": delivery_2.move_ids.location_id.id,
                    "location_dest_id": delivery_2.move_ids.location_dest_id.id,
                    "lot_id": good_lot.id,
                    "product_id": self.apple_product.id,
                    "product_uom_id": self.apple_product.uom_id.id,
                    "quantity": 4,
                },
            ),
            (
                0,
                0,
                {
                    "company_id": self.env.company.id,
                    "location_id": delivery_2.move_ids.location_id.id,
                    "location_dest_id": delivery_2.move_ids.location_dest_id.id,
                    "lot_id": expired_lot_1.id,
                    "product_id": self.apple_product.id,
                    "product_uom_id": self.apple_product.uom_id.id,
                    "quantity": 4,
                },
            ),
        ]
        delivery_2.move_ids.picked = True
        res = delivery_2.button_validate()
        self.assertNotEqual(res, True)
        self.assertEqual(res["res_model"], "expiry.picking.confirmation")

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        delivery_3 = picking_form.save()
        delivery_3.action_confirm()
        delivery_3.move_line_ids = [
            (5, 0),
            (
                0,
                0,
                {
                    "company_id": self.env.company.id,
                    "location_id": delivery_3.move_ids.location_id.id,
                    "location_dest_id": delivery_3.move_ids.location_dest_id.id,
                    "lot_id": expired_lot_1.id,
                    "product_id": self.apple_product.id,
                    "product_uom_id": self.apple_product.uom_id.id,
                    "quantity": 4,
                },
            ),
        ]
        delivery_3.move_ids.picked = True
        res = delivery_3.button_validate()
        self.assertNotEqual(res, True)
        self.assertEqual(res["res_model"], "expiry.picking.confirmation")

    def test_edit_removal_date_in_inventory_mode(self):
        self.demo_user = mail_new_test_user(
            self.env,
            name="Demo user",
            login="userdemo",
            email="d.d@example.com",
            groups="stock.group_stock_manager",
        )
        lot_form = Form(self.LotObj)
        lot_form.name = "LOT001"
        lot_form.product_id = self.apple_product
        apple_lot = lot_form.save()

        quant = self.StockQuantObj.with_context(inventory_mode=True).create(
            {
                "product_id": self.apple_product.id,
                "location_id": self.stock_location.id,
                "quantity": 10,
                "lot_id": apple_lot.id,
            }
        )
        new_date = datetime.today() + timedelta(days=15)
        quant.with_user(self.demo_user).with_context(inventory_mode=True).write(
            {"removal_date": new_date}
        )
        self.assertEqual(quant.removal_date, new_date)

    def test_apply_lot_date_on_sml(self):
        exp_date = fields.Datetime.today() + relativedelta(days=15)
        sml_exp_date = fields.Datetime.today() + relativedelta(days=10)

        lot = self.env["stock.lot"].create(
            {
                "name": "Lot 1",
                "product_id": self.apple_product.id,
                "expiration_date": fields.Datetime.to_string(exp_date),
            }
        )

        move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.apple_product.id,
                "product_uom_id": self.apple_product.uom_id.id,
            }
        )
        sml = self.env["stock.move.line"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.apple_product.id,
                "quantity": 3,
                "product_uom_id": self.apple_product.uom_id.id,
                "expiration_date": fields.Datetime.to_string(sml_exp_date),
                "company_id": self.env.company.id,
                "move_id": move.id,
            }
        )
        self.assertEqual(sml.expiration_date, sml_exp_date)

        sml.lot_id = lot
        self.assertEqual(sml.expiration_date, exp_date)

    def test_apply_same_date_on_expiry_fields(self):
        expiration_time = 10
        self.apple_product.write(
            {
                "expiration_time": expiration_time,
                "use_time": 0,
                "removal_time": 0,
                "alert_time": 0,
            }
        )

        lot = self.env["stock.lot"].create(
            {
                "product_id": self.apple_product.id,
            }
        )

        delta = timedelta(seconds=10)
        expiration_date = datetime.today() + timedelta(days=expiration_time)
        err_msg = "The time on the product is set to 0, it means that the corresponding date should be the same as the expiration one"
        self.assertAlmostEqual(lot.expiration_date, expiration_date, delta=delta)
        self.assertAlmostEqual(lot.use_date, expiration_date, delta=delta, msg=err_msg)
        self.assertAlmostEqual(
            lot.removal_date, expiration_date, delta=delta, msg=err_msg
        )
        self.assertAlmostEqual(
            lot.alert_date, expiration_date, delta=delta, msg=err_msg
        )

    def test_no_expiration_date(self):
        lot_form = Form(self.LotObj)
        lot_form.name = "LOT001"
        lot_form.product_id = self.apple_product
        apple_lot = lot_form.save()

        lot_form = Form(apple_lot)
        lot_form.expiration_date = False
        lot_form.use_date = False
        lot_form.removal_date = False
        lot_form.alert_date = False
        apple_lot = lot_form.save()

        self.StockQuantObj.with_context(inventory_mode=True).create(
            {
                "product_id": self.apple_product.id,
                "location_id": self.stock_location.id,
                "quantity": 100,
                "lot_id": apple_lot.id,
            }
        )

        self.assertEqual(self.apple_product.qty_available, 100, "Wrong quantity.")

        picking_out = self.PickingObj.create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "state": "draft",
            }
        )

        self.MoveObj.create(
            {
                "product_id": self.apple_product.id,
                "product_uom_qty": 10,
                "product_uom_id": self.apple_product.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )

        self.assertEqual(
            picking_out.move_ids.state, "draft", "Wrong state of move line."
        )
        picking_out.action_confirm()
        picking_out.action_assign()
        self.assertEqual(
            picking_out.move_ids.state, "assigned", "Wrong state of move line."
        )

    def test_no_lot(self):
        fefo_strategy = self.env["product.removal"].search([("method", "=", "fefo")])
        self.apple_product.categ_id.removal_strategy_id = fefo_strategy.id

        apple_lot = self.LotObj.create(
            {
                "name": "LOT001",
                "product_id": self.apple_product.id,
            }
        )

        self.StockQuantObj.with_context(inventory_mode=True).create(
            [
                {
                    "product_id": self.apple_product.id,
                    "location_id": self.stock_location.id,
                    "quantity": 100,
                },
                {
                    "product_id": self.apple_product.id,
                    "location_id": self.stock_location.id,
                    "quantity": 100,
                    "lot_id": apple_lot.id,
                },
            ]
        )

        with Form(self.PickingObj) as picking_form:
            picking_form.picking_type_id = self.picking_type_out
            with picking_form.move_ids.new() as move:
                move.product_id = self.apple_product
                move.product_uom_qty = 10
            picking_out = picking_form.save()

        picking_out.action_assign()
        self.assertEqual(picking_out.move_line_ids.lot_id, apple_lot)

    def test_compute_expiration_date_from_date_planned(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Apple's Joe",
                "company_id": self.env.ref("base.main_company").id,
            }
        )

        delta = timedelta(seconds=10)
        new_date = datetime.today() + timedelta(days=42)
        expiration_date = new_date + timedelta(days=self.apple_product.expiration_time)

        picking_form = Form(self.env["stock.picking"])
        picking_form.partner_id = partner
        picking_form.date_planned = new_date
        picking_form.picking_type_id = self.picking_type_in

        with picking_form.move_ids.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        delivery = picking_form.save()
        delivery.action_confirm()

        self.assertAlmostEqual(
            delivery.move_line_ids[0].expiration_date, expiration_date, delta=delta
        )

    def test_compute_display_name(self):
        apple_lot1 = self.LotObj.create(
            {
                "name": "LOT-00001",
                "product_id": self.apple_product.id,
                "expiration_date": False,
                "alert_date": False,
            }
        )
        apple_lot2 = self.LotObj.create(
            {
                "name": "LOT-00002",
                "product_id": self.apple_product.id,
                "expiration_date": datetime.today() - timedelta(days=10),
            }
        )
        apple_lot3 = self.LotObj.create(
            {
                "name": "LOT-00003",
                "product_id": self.apple_product.id,
                "alert_date": datetime.today() - timedelta(days=10),
            }
        )
        self.assertEqual(
            apple_lot1.with_context(formatted_display_name=True).display_name,
            "LOT-00001",
        )
        self.assertEqual(
            apple_lot2.with_context(formatted_display_name=True).display_name,
            "LOT-00002\t--Expired--",
        )
        self.assertEqual(
            apple_lot3.with_context(formatted_display_name=True).display_name,
            "LOT-00003\t--Expire on "
            + fields.Datetime.to_string(apple_lot3.expiration_date)
            + "--",
        )

    def test_proceed_except_expired_delivery_without_move_removal_date(self):
        lot = self.LotObj.create(
            {
                "name": "LOT-001",
                "product_id": self.apple_product.id,
            }
        )
        lot.removal_date = False

        self.StockQuantObj.with_context(inventory_mode=True).create(
            {
                "product_id": self.apple_product.id,
                "location_id": self.stock_location.id,
                "quantity": 100,
                "lot_id": lot.id,
            }
        )
        picking = self.PickingObj.create(
            {
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_out.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.apple_product.id,
                            "product_uom_qty": 2,
                        }
                    )
                ],
            }
        )
        picking.button_validate()
        context = {
            "button_validate_picking_ids": [picking.id],
            "default_picking_ids": [picking.id],
            "default_lot_ids": [lot.id],
        }
        wizard = (
            self.env["expiry.picking.confirmation"].with_context(context).create({})
        )
        self.assertFalse(wizard.picking_ids.move_line_ids.removal_date)
        wizard.process_no_expired()

    def test_reordering_rule_for_expiring_product(self):
        receipt = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner_1.id,
                "picking_type_id": self.picking_type_in.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.apple_product.id,
                            "product_uom_qty": 10.0,
                        }
                    )
                ],
            }
        )
        receipt.action_confirm()
        receipt.move_ids.lot_ids = self.LotObj.create(
            {
                "name": "Lot1",
                "product_id": self.apple_product.id,
            }
        )
        receipt.button_validate()
        reordering_rule = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.apple_product.id,
                "product_max_qty": 10,
                "product_min_qty": 5,
            }
        )
        self.assertEqual(self.env.company.stock_config_id.horizon_days, 365)
        self.assertRecordValues(
            reordering_rule, [{"qty_forecast": 10, "qty_to_order": 0}]
        )

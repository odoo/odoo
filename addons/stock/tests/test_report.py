from datetime import date, datetime, timedelta
from re import findall, sub

from odoo import Command
from odoo.tests import Form, TransactionCase

from odoo.addons.stock.tests.common import RECEPTION_ROUTE_BOUGHT, is_module_installed


class TestReportsCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.ModelDataObj = cls.env["ir.model.data"]
        cls.picking_type_in = cls.env["stock.picking.type"].browse(
            cls.ModelDataObj._xmlid_to_res_id("stock.picking_type_in")
        )
        cls.picking_type_out = cls.env["stock.picking.type"].browse(
            cls.ModelDataObj._xmlid_to_res_id("stock.picking_type_out")
        )
        cls.supplier_location = cls.env["stock.location"].browse(
            cls.ModelDataObj._xmlid_to_res_id("stock.stock_location_suppliers")
        )
        cls.stock_location = cls.env["stock.location"].browse(
            cls.ModelDataObj._xmlid_to_res_id("stock.stock_location_stock")
        )

        cls.product1 = cls.env["product.product"].create(
            {
                "name": 'Mellohi"',
                "is_storable": True,
                "categ_id": cls.env.ref("product.product_category_goods").id,
                "tracking": "lot",
                "default_code": 'C4181234""154654654654',
                "barcode": 'scan""me',
            }
        )
        cls.serial_product = cls.env["product.product"].create(
            {
                "name": "simple prod",
                "is_storable": True,
                "tracking": "serial",
            }
        )

        product_form = Form(cls.env["product.product"])
        product_form.is_storable = True
        product_form.name = "Product"
        product_form.categ_id = cls.env.ref("product.product_category_goods")
        cls.product = product_form.save()
        cls.product_template = cls.product.product_tmpl_id
        cls.wh_2 = cls.env["stock.warehouse"].create(
            {
                "name": "Evil Twin Warehouse",
                "code": "ETWH",
            }
        )

    def get_report_forecast(
        self, product_template_ids=False, product_variant_ids=False, context=False
    ):
        if product_template_ids:
            report = self.env["stock.forecasted_product_template"]
            product_ids = product_template_ids
        elif product_variant_ids:
            report = self.env["stock.forecasted_product_product"]
            product_ids = product_template_ids
        if context:
            report = report.with_context(context)
        report_values = report.get_report_values(docids=product_ids)
        docs = report_values["docs"]
        lines = docs["lines"]
        return report_values, docs, lines

    def sum_dicts(self, dicts, key):
        res = {}
        for d in dicts.values():
            for k, v in d.get(key, {}).items():
                res[k] = res.get(k, 0) + v
        return res


class TestReports(TestReportsCommon):
    def _assert_zpl_equal(self, target, rendering, msg):
        # ZPL ignores whitespace between commands, and the XML formatters reflow these
        # templates' indentation and blank lines.
        def normalise(zpl):
            return sub(rb"\n+", b"\n", zpl.replace(b" ", b""))

        self.assertEqual(normalise(target), normalise(rendering), msg)

    def _check_closure_commands(self, zpl_rendered_template):
        wrong_xz_count = findall(r"\^XZ[^\\]+[^n]", str(zpl_rendered_template))
        self.assertFalse(wrong_xz_count, "invalid closure command")

    def test_product_label_reports(self):
        report = self.env.ref("stock.label_product_product")
        target = b'\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FDscan""me^FS\n^XZ\n\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FDscan""me^FS\n^XZ\n'
        rendering, qweb_type = report._render_qweb_text(
            "stock.label_product_product",
            self.product1.product_tmpl_id.id,
            {
                "quantity_by_product": {self.product1.product_tmpl_id.id: 2},
                "active_model": "product.template",
                "zpl_template": "normal",
            },
        )
        self._check_closure_commands(rendering)
        self._assert_zpl_equal(
            target,
            rendering,
            "Product name, default code or barcode is not correctly rendered, make sure the quotes are escaped correctly",
        )
        self.assertEqual(qweb_type, "text", "the report type is not good")

    def test_product_label_custom_barcode_reports(self):
        report = self.env.ref("stock.label_product_product")
        target = b'\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FD123"barcode^FS\n^XZ\n\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FD123"barcode^FS\n^XZ\n\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FDbarcode"456^FS\n^XZ\n\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^FO35,77^BY2^BCN,100,Y,N,N^FDbarcode"456^FS\n^XZ\n'
        rendering, qweb_type = report._render_qweb_text(
            "stock.label_product_product",
            self.product1.product_tmpl_id.id,
            {
                "custom_barcodes": {
                    self.product1.product_tmpl_id.id: [
                        ('123"barcode', 2),
                        ('barcode"456', 2),
                    ]
                },
                "quantity_by_product": {},
                "active_model": "product.template",
                "zpl_template": "normal",
            },
        )
        self._check_closure_commands(rendering)
        self._assert_zpl_equal(
            target,
            rendering,
            "Custom barcodes are most likely not corretly rendered, make sure the quotes are escaped correctly",
        )
        self.assertEqual(qweb_type, "text", "the report type is not good")

    def test_reports_with_special_characters(self):
        product_test = self.env["product.product"].create(
            {
                "name": 'Mellohi"',
                "is_storable": True,
                "tracking": "lot",
                "default_code": 'C4181234""154654654654',
                "barcode": "9745213796142",
            }
        )

        lot1 = self.env["stock.lot"].create(
            {
                "name": 'Volume-Beta"',
                "product_id": product_test.id,
            }
        )
        self.env.user.group_ids += self.env.ref("stock.group_stock_lot_print_gs1")
        report = self.env.ref("stock.label_lot_template")
        target = b'\n\n^XA^CI28\n^FO100,50\n^A0N,44,33^FD[C4181234""154654654654]Mellohi"^FS\n^FO100,100\n^A0N,44,33^FDLN/SN:Volume-Beta"^FS\n^FO425,150^BY3\n^BXN,8,200\n^FD010974521379614210Volume-Beta"^FS\n^XZ\n'

        rendering, qweb_type = report._render_qweb_text(
            "stock.label_lot_template", lot1.id
        )
        self._check_closure_commands(rendering)
        self._assert_zpl_equal(
            target,
            rendering,
            "The rendering is not good, make sure quotes are correctly escaped",
        )
        self.assertEqual(qweb_type, "text", "the report type is not good")

    def test_reports_product_no_barcode(self):
        report = self.env.ref("stock.label_product_product")
        self.product1.barcode = False
        target = b'\n\n^XA^CI28\n\n^FT35,40^A0N,25^FD[C4181234""154654654654]Mellohi"^FS\n^XZ\n'
        rendering, qweb_type = report._render_qweb_text(
            "stock.label_product_product",
            self.product1.product_tmpl_id.id,
            {
                "quantity_by_product": {self.product1.product_tmpl_id.id: 1},
                "active_model": "product.template",
                "zpl_template": "normal",
            },
        )
        self._assert_zpl_equal(
            target,
            rendering,
            "Product name, default code or barcode is not correctly rendered, make sure the quotes are escaped correctly",
        )
        self.assertEqual(qweb_type, "text", "the report type is not good")

    def test_report_quantity_1(self):
        product_form = Form(self.env["product.product"])
        product_form.is_storable = True
        product_form.name = "Product"
        product = product_form.save()

        warehouse = self.env["stock.warehouse"].search([], limit=1)
        stock = self.env["stock.location"].create(
            {
                "name": "New Stock",
                "usage": "internal",
                "location_id": warehouse.view_location_id.id,
            }
        )

        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": stock.id,
                "inventory_quantity": 50,
            }
        ).action_apply_inventory()
        self.env.flush_all()
        report_records_today = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            [],
            ["product_qty:sum"],
        )
        report_records_tomorrow = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() + timedelta(days=1)),
            ],
            [],
            ["product_qty:sum"],
        )
        report_records_yesterday = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() - timedelta(days=1)),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records_today[0][0], 50.0)
        self.assertEqual(report_records_tomorrow[0][0], 50.0)
        self.assertEqual(report_records_yesterday[0][0], 0.0)

        move_out = self.env["stock.move"].create(
            {
                "date": datetime.now() + timedelta(days=1),
                "location_id": stock.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 20.0,
            }
        )
        self.env.flush_all()
        report_records_tomorrow = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() + timedelta(days=1)),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records_tomorrow[0][0], 50.0)
        move_out._action_confirm()
        self.env.flush_all()
        report_records_tomorrow = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() + timedelta(days=1)),
            ],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "forecast"
            ),
            30.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "out"
            ),
            -20.0,
        )
        report_records_today = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_today
                if state == "forecast"
            ),
            50.0,
        )

        move_in = self.env["stock.move"].create(
            {
                "date": datetime.now() + timedelta(days=1),
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": stock.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10.0,
            }
        )
        move_in._action_confirm()
        self.env.flush_all()
        report_records_tomorrow = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() + timedelta(days=1)),
            ],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "forecast"
            ),
            40.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "out"
            ),
            -20.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "in"
            ),
            10.0,
        )
        report_records_today = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_today
                if state == "forecast"
            ),
            50.0,
        )

        move_out = self.env["stock.move"].create(
            {
                "date": datetime.now() - timedelta(days=1),
                "location_id": stock.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 30.0,
            }
        )
        move_out._action_confirm()
        self.env.flush_all()
        report_records_today = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            ["state"],
            ["product_qty:sum"],
        )
        report_records_tomorrow = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() + timedelta(days=1)),
            ],
            ["state"],
            ["product_qty:sum"],
        )
        report_records_yesterday = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today() - timedelta(days=1)),
            ],
            ["state"],
            ["product_qty:sum"],
        )

        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_yesterday
                if state == "forecast"
            ),
            -30.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_yesterday
                if state == "out"
            ),
            -30.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_yesterday
                if state == "in"
            ),
            0.0,
        )

        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_today
                if state == "forecast"
            ),
            20.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_today
                if state == "out"
            ),
            0.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_today
                if state == "in"
            ),
            0.0,
        )

        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "forecast"
            ),
            10.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "out"
            ),
            -20.0,
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records_tomorrow
                if state == "in"
            ),
            10.0,
        )

    def test_report_quantity_2(self):
        product_form = Form(self.env["product.product"])
        product_form.is_storable = True
        product_form.name = "Product"
        product = product_form.save()

        warehouse = self.env["stock.warehouse"].search([], limit=1)
        stock = self.env["stock.location"].create(
            {
                "name": "Stock Under Warehouse",
                "usage": "internal",
                "location_id": warehouse.view_location_id.id,
            }
        )
        stock_without_wh = self.env["stock.location"].create(
            {
                "name": "Stock Outside Warehouse",
                "usage": "internal",
            }
        )
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": stock.id,
                "inventory_quantity": 50,
            }
        ).action_apply_inventory()
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": stock_without_wh.id,
                "inventory_quantity": 50,
            }
        ).action_apply_inventory()
        move = self.env["stock.move"].create(
            {
                "location_id": stock.id,
                "location_dest_id": stock_without_wh.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10.0,
            }
        )
        move._action_confirm()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("product_id", "=", product.id),
                ("date", "=", date.today()),
                ("warehouse_id", "!=", False),
            ],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records
                if state == "forecast"
            ),
            40.0,
        )
        report_records = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records
                if state == "forecast"
            ),
            40.0,
        )
        move = self.env["stock.move"].create(
            {
                "location_id": stock_without_wh.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10.0,
            }
        )
        move._action_confirm()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            ["state"],
            ["product_qty:sum"],
        )
        self.assertEqual(
            sum(
                product_qty
                for state, product_qty in report_records
                if state == "forecast"
            ),
            40.0,
        )

    def test_report_quantity_3(self):
        product_form = Form(self.env["product.product"])
        product_form.is_storable = True
        product_form.name = "Product"
        product = product_form.save()

        warehouse = self.env["stock.warehouse"].search([], limit=1)
        stock = self.env["stock.location"].create(
            {
                "name": "Rack",
                "usage": "view",
                "location_id": warehouse.view_location_id.id,
            }
        )
        stock_real_loc = self.env["stock.location"].create(
            {
                "name": "Drawer",
                "usage": "internal",
                "location_id": stock.id,
            }
        )

        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], 0.0)

        move_in = self.env["stock.move"].create(
            {
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": stock.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 20.0,
            }
        )
        move_in._action_confirm()
        move_in.move_line_ids.location_dest_id = stock_real_loc.id
        move_in.move_line_ids.quantity = 20.0
        move_in.picked = True
        move_in._action_done()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], 20.0)

        move_out = self.env["stock.move"].create(
            {
                "location_id": stock.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 10.0,
            }
        )
        move_out._action_confirm()
        move_out._action_assign()
        move_out.move_line_ids.quantity = 10.0
        move_out.picked = True
        move_out._action_done()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [("product_id", "=", product.id), ("date", "=", date.today())],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], 10.0)

    def test_report_quantity_4(self):
        now = datetime.now()
        customer_loc, supplier_loc = self.env[
            "stock.warehouse"
        ]._get_partner_locations()
        self.wh_2.write({"reception_steps": "two_steps", "delivery_steps": "pick_ship"})

        move_pick = self.env["stock.move"].create(
            {
                "picking_type_id": self.wh_2.pick_type_id.id,
                "location_id": self.wh_2.lot_stock_id.id,
                "location_final_id": customer_loc.id,
                "product_id": self.product1.id,
                "product_uom_qty": 5.0,
                "date": now + timedelta(days=2),
            }
        )
        move_pick._action_confirm()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("state", "=", "forecast"),
                ("product_id", "=", self.product1.id),
                ("date", "=", now.date()),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertFalse(
            report_records[0][0], "Forecast should still be at 0 today, so no records."
        )
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("state", "=", "forecast"),
                ("product_id", "=", self.product1.id),
                ("date", "=", (now + timedelta(days=2)).date()),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], -5)

        move_in = self.env["stock.move"].create(
            {
                "picking_type_id": self.wh_2.in_type_id.id,
                "location_id": supplier_loc.id,
                "location_final_id": self.wh_2.lot_stock_id.id,
                "product_id": self.product1.id,
                "product_uom_qty": 10.0,
                "date": now + timedelta(days=1),
            }
        )
        move_in._action_confirm()
        self.env.flush_all()
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("state", "=", "forecast"),
                ("product_id", "=", self.product1.id),
                ("date", "=", now.date()),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertFalse(
            report_records[0][0], "Forecast should still be at 0 today, so no records."
        )
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("state", "=", "forecast"),
                ("product_id", "=", self.product1.id),
                ("date", "=", (now + timedelta(days=1)).date()),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], 10)
        report_records = self.env["report.stock.quantity"]._read_group(
            [
                ("state", "=", "forecast"),
                ("product_id", "=", self.product1.id),
                ("date", "=", (now + timedelta(days=2)).date()),
            ],
            [],
            ["product_qty:sum"],
        )
        self.assertEqual(report_records[0][0], 5)

    def test_report_forecast_1(self):
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 0)
        self.assertEqual(draft_picking_qty["out"], 0)

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        receipt = receipt_form.save()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 2)
        self.assertEqual(draft_picking_qty["out"], 0)

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery = delivery_form.save()
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery = delivery_form.save()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 2)
        self.assertEqual(draft_picking_qty["out"], 5)

        delivery.action_confirm()
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 2)
        self.assertEqual(draft_picking_qty["out"], 0)
        delivery_line = lines[0]
        self.assertEqual(delivery_line["quantity"], 5)
        self.assertEqual(delivery_line["replenishment_filled"], False)
        self.assertEqual(delivery_line["document_out"]["id"], delivery.id)

        receipt.action_confirm()
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 2, "Must have 2 line.")
        self.assertEqual(draft_picking_qty["in"], 0)
        self.assertEqual(draft_picking_qty["out"], 0)
        fulfilled_line = lines[0]
        unavailable_line = lines[1]
        self.assertEqual(fulfilled_line["replenishment_filled"], True)
        self.assertEqual(fulfilled_line["quantity"], 2)
        self.assertEqual(fulfilled_line["document_in"]["id"], receipt.id)
        self.assertEqual(fulfilled_line["document_out"]["id"], delivery.id)
        self.assertEqual(unavailable_line["replenishment_filled"], False)
        self.assertEqual(unavailable_line["quantity"], 3)
        self.assertEqual(unavailable_line["document_out"]["id"], delivery.id)

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        receipt2 = receipt_form.save()
        receipt2.action_confirm()

        receipt_form = Form(receipt)
        with receipt_form.move_ids.edit(0) as move_line:
            move_line.quantity = 2
        receipt = receipt_form.save()
        receipt.move_ids.picked = True
        receipt.button_validate()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 2, "Still must have 2 line.")
        self.assertEqual(draft_picking_qty["in"], 0)
        self.assertEqual(draft_picking_qty["out"], 0)
        line1 = lines[0]
        line2 = lines[1]
        self.assertEqual(line1["quantity"], 2)
        self.assertEqual(line1["replenishment_filled"], True)
        self.assertEqual(line1["document_in"], False)
        self.assertEqual(line1["document_out"]["id"], delivery.id)
        self.assertEqual(line2["quantity"], 3)
        self.assertEqual(line2["replenishment_filled"], True)
        self.assertEqual(line2["document_in"]["id"], receipt2.id)
        self.assertEqual(line2["document_out"]["id"], delivery.id)

    def test_report_forecast_2_replenishments_order(self):
        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 6
        receipt = receipt_form.save()
        receipt.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery = delivery_form.save()
        delivery.action_confirm()

        _report_values, _docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        self.assertEqual(len(lines), 2, "Must have 2 line.")
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1["document_in"]["id"], receipt.id)
        self.assertEqual(line_1["document_out"]["id"], delivery.id)
        self.assertEqual(line_2["document_in"]["id"], receipt.id)
        self.assertEqual(line_2["document_out"], False)

    def test_report_forecast_3_sort_by_date(self):
        today = datetime.today()
        one_hours = timedelta(hours=1)
        one_day = timedelta(days=1)
        one_month = timedelta(days=30)
        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_1 = delivery_form.save()
        delivery_1.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today + one_hours
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_2 = delivery_form.save()
        delivery_2.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today - one_hours
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_3 = delivery_form.save()
        delivery_3.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today + one_day
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_4 = delivery_form.save()
        delivery_4.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today - one_day
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_5 = delivery_form.save()
        delivery_5.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today + one_month
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_6 = delivery_form.save()
        delivery_6.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = today - one_month
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_7 = delivery_form.save()
        delivery_7.action_confirm()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 7, "The report must have 7 line.")
        self.assertEqual(draft_picking_qty["in"], 0)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery_7.id)
        self.assertEqual(lines[1]["document_out"]["id"], delivery_5.id)
        self.assertEqual(lines[2]["document_out"]["id"], delivery_3.id)
        self.assertEqual(lines[3]["document_out"]["id"], delivery_1.id)
        self.assertEqual(lines[4]["document_out"]["id"], delivery_2.id)
        self.assertEqual(lines[5]["document_out"]["id"], delivery_4.id)
        self.assertEqual(lines[6]["document_out"]["id"], delivery_6.id)

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = today + one_month
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        receipt_1 = receipt_form.save()
        receipt_1.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = today - one_month
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        receipt_2 = receipt_form.save()
        receipt_2.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = today - one_hours
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 10
        receipt_3 = receipt_form.save()
        receipt_3.action_confirm()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 7, "The report must have 7 line.")
        self.assertEqual(draft_picking_qty["in"], 0)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery_7.id)
        self.assertEqual(lines[0]["document_in"]["id"], receipt_2.id)
        self.assertEqual(lines[0]["is_late"], False)
        self.assertEqual(lines[1]["document_out"]["id"], delivery_5.id)
        self.assertEqual(lines[1]["document_in"]["id"], receipt_3.id)
        self.assertEqual(lines[1]["is_late"], True)
        self.assertEqual(lines[2]["document_out"]["id"], delivery_3.id)
        self.assertEqual(lines[2]["document_in"]["id"], receipt_3.id)
        self.assertEqual(lines[2]["is_late"], False)
        self.assertEqual(lines[3]["document_out"]["id"], delivery_1.id)
        self.assertEqual(lines[3]["document_in"]["id"], receipt_1.id)
        self.assertEqual(lines[3]["is_late"], True)
        self.assertEqual(lines[4]["document_out"]["id"], delivery_2.id)
        self.assertEqual(lines[4]["document_in"], False)
        self.assertEqual(lines[5]["document_out"]["id"], delivery_4.id)
        self.assertEqual(lines[5]["document_in"], False)
        self.assertEqual(lines[6]["document_out"]["id"], delivery_6.id)
        self.assertEqual(lines[6]["document_in"], False)

    def test_report_forecast_4_intermediate_transfers(self):
        # the three-step reception route pulls from Vendors with stock alone
        if is_module_installed(self.env, "purchase_stock"):
            self.skipTest(RECEPTION_ROUTE_BOUGHT)
        grp_multi_loc = self.env.ref("stock.group_stock_multi_locations")
        grp_multi_routes = self.env.ref("stock.group_adv_location")
        self.env.user.write({"group_ids": [(4, grp_multi_loc.id)]})
        self.env.user.write({"group_ids": [(4, grp_multi_routes.id)]})
        warehouse = self.env.ref("stock.warehouse0")
        warehouse.reception_steps = "three_steps"
        self.product.write(
            {
                "route_ids": [
                    (4, self.env.ref("stock.route_warehouse0_mto").id),
                    (4, warehouse.reception_route_id.id),
                ]
            }
        )
        reordering_rule = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "Product RR",
                "location_id": warehouse.lot_stock_id.id,
                "product_id": self.product.id,
                "product_min_qty": 5,
                "product_max_qty": 10,
            }
        )
        reordering_rule.action_replenish()
        _report_values, _docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        pickings = self.env["stock.picking"].search(
            [("product_id", "=", self.product.id)]
        )
        receipt = pickings.filtered(
            lambda p: p.picking_type_id.id == self.picking_type_in.id
        )

        self.assertEqual(len(lines), 2, "The report must have only 2 lines.")
        self.assertEqual(
            lines[1]["document_in"]["id"],
            receipt.id,
            "The report must only show the receipt.",
        )
        self.assertEqual(lines[1]["document_out"], False)
        self.assertEqual(lines[1]["quantity"], reordering_rule.product_max_qty)

    def test_report_forecast_5_multi_warehouse(self):
        wh_2 = self.wh_2
        picking_type_out_2 = self.env["stock.picking.type"].search(
            [
                ("code", "=", "outgoing"),
                ("warehouse_id", "=", wh_2.id),
            ]
        )

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery = delivery_form.save()
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery = delivery_form.save()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["out"], 5)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)

        delivery.action_confirm()
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery.id)
        self.assertEqual(lines[0]["quantity"], 5)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_out_2
        delivery_2 = delivery_form.save()
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 8
        delivery_2 = delivery_form.save()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery.id)
        self.assertEqual(lines[0]["quantity"], 5)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 8)
        delivery_2.action_confirm()
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery.id)
        self.assertEqual(lines[0]["quantity"], 5)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty["out"], 0)
        self.assertEqual(lines[0]["document_out"]["id"], delivery_2.id)
        self.assertEqual(lines[0]["quantity"], 8)

    def test_report_forecast_5_multi_warehouse_chain(self):
        wh_2 = self.wh_2
        wh = self.env.ref("stock.warehouse0")
        replenish_route = self.env["stock.route"].create(
            {
                "name": "replenish",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "replenish",
                            "action": "pull",
                            "location_src_id": wh_2.lot_stock_id.id,
                            "location_dest_id": wh.lot_stock_id.id,
                            "picking_type_id": wh_2.int_type_id.id,
                            "location_dest_from_rule": True,
                        }
                    )
                ],
            }
        )
        self.env.ref("stock.route_warehouse0_mto").active = True
        self.product.route_ids = [
            Command.set(
                [self.env.ref("stock.route_warehouse0_mto").id, replenish_route.id]
            )
        ]
        self.env["stock.quant"]._update_available_quantity(
            self.product, wh_2.lot_stock_id, 5
        )

        delivery = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": wh.out_type_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5,
                            "product_uom_id": self.product.uom_id.id,
                            "location_id": wh.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                            "procure_method": "make_to_order",
                        }
                    )
                ],
            }
        )
        delivery.action_confirm()

        inter_wh_delivery = self.env["stock.move"].search(
            [
                ("picking_type_id", "=", wh_2.int_type_id.id),
                ("location_id", "=", wh_2.lot_stock_id.id),
                ("location_dest_id", "=", wh.lot_stock_id.id),
                ("product_id", "=", self.product.id),
            ]
        )
        self.assertEqual(len(inter_wh_delivery), 1)
        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh.id},
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["document_out"]["id"], delivery.id)
        self.assertEqual(lines[0]["document_in"]["id"], inter_wh_delivery.picking_id.id)

    def test_report_forecast_6_multi_company(self):
        company_2 = self.env["res.company"].create({"name": "Aperture Science"})
        wh_2 = self.env["stock.warehouse"].search([("company_id", "=", company_2.id)])
        wh_2_picking_type_in = wh_2.in_type_id

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        wh_1_receipt = receipt_form.save()
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        wh_1_receipt = receipt_form.save()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = wh_2_picking_type_in
        wh_2_receipt = receipt_form.save()
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        wh_2_receipt = receipt_form.save()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 2)
        self.assertEqual(draft_picking_qty["out"], 0)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        draft_picking_qty = self.sum_dicts(docs["product"], "draft_picking_qty")
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty["in"], 5)
        self.assertEqual(draft_picking_qty["out"], 0)

        wh_1_receipt.action_confirm()
        wh_2_receipt.action_confirm()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        self.assertEqual(len(lines), 2, "Must have 2 lines.")
        self.assertEqual(lines[1]["document_in"]["id"], wh_1_receipt.id)
        self.assertEqual(lines[1]["quantity"], 2)

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={"warehouse_id": wh_2.id},
        )
        self.assertEqual(len(lines), 2, "Must have 2 lines.")
        self.assertEqual(lines[1]["document_in"]["id"], wh_2_receipt.id)
        self.assertEqual(lines[1]["quantity"], 5)

    def test_report_forecast_7_multiple_variants(self):
        product_attr_color = self.env["product.attribute"].create({"name": "Color"})
        color_gray = self.env["product.attribute.value"].create(
            {
                "name": "Old Fashioned Gray",
                "attribute_id": product_attr_color.id,
            }
        )
        color_blue = self.env["product.attribute.value"].create(
            {
                "name": "Electric Blue",
                "attribute_id": product_attr_color.id,
            }
        )
        product_attr_size = self.env["product.attribute"].create({"name": "size"})
        size_pocket = self.env["product.attribute.value"].create(
            {
                "name": "Pocket",
                "attribute_id": product_attr_size.id,
            }
        )
        size_xl = self.env["product.attribute.value"].create(
            {
                "name": "XL",
                "attribute_id": product_attr_size.id,
            }
        )

        product_template = self.env["product.template"].create(
            {
                "name": "Game Joy",
                "is_storable": True,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": product_attr_color.id,
                            "value_ids": [(6, 0, [color_gray.id, color_blue.id])],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "attribute_id": product_attr_size.id,
                            "value_ids": [(6, 0, [size_pocket.id, size_xl.id])],
                        },
                    ),
                ],
            }
        )
        gamejoy_pocket_gray = product_template.product_variant_ids[0]
        gamejoy_xl_gray = product_template.product_variant_ids[1]
        gamejoy_pocket_blue = product_template.product_variant_ids[2]
        gamejoy_xl_blue = product_template.product_variant_ids[3]

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 8
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_pocket_blue
            move_line.product_uom_qty = 4
        receipt_1 = receipt_form.save()
        receipt_1.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 2
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_xl_gray
            move_line.product_uom_qty = 10
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_xl_blue
            move_line.product_uom_qty = 12
        receipt_2 = receipt_form.save()
        receipt_2.action_confirm()

        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=product_template.ids
        )
        self.assertEqual(len(lines), 9, "Must have 9 lines.")
        self.assertTrue(
            all(
                product_variant["id"] in product_template.product_variant_ids.ids
                for product_variant in docs["product_variants"]
            )
        )

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 10
        delivery = delivery_form.save()
        delivery.action_confirm()

        gamejoy_pocket_blue.action_archive()
        _report_values, docs, lines = self.get_report_forecast(
            product_template_ids=product_template.ids
        )
        self.assertEqual(
            len(lines),
            6,
            "Must exclude the archived product and therefore have 6 lines",
        )
        self.assertEqual(
            docs["product_variants_ids"], product_template.product_variant_ids.ids
        )
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1["product"]["id"], gamejoy_pocket_gray.id)
        self.assertEqual(line_1["quantity"], 8)
        self.assertTrue(line_1["replenishment_filled"])
        self.assertEqual(line_1["document_in"]["id"], receipt_1.id)
        self.assertEqual(line_1["document_out"]["id"], delivery.id)
        self.assertEqual(line_2["product"]["id"], gamejoy_pocket_gray.id)
        self.assertEqual(line_2["quantity"], 2)
        self.assertTrue(line_2["replenishment_filled"])
        self.assertEqual(line_2["document_in"]["id"], receipt_2.id)
        self.assertEqual(line_2["document_out"]["id"], delivery.id)

    def test_report_forecast_8_delivery_to_receipt_link(self):
        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        receipt = receipt_form.save()
        receipt.move_ids[0].write(
            {
                "move_dest_ids": [(4, delivery2.move_ids[0].id)],
            }
        )
        receipt.action_confirm()

        self.assertEqual(delivery.move_ids.forecast_availability, -100)
        self.assertEqual(delivery2.move_ids.forecast_availability, 200)
        self.assertFalse(delivery.move_ids.date_planned_forecast)
        self.assertEqual(
            delivery2.move_ids.date_planned_forecast, receipt.move_ids.date
        )

        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )

        self.assertEqual(len(lines), 2, "Only 2 lines")
        delivery_line = [l for l in lines if l["document_out"]["id"] == delivery.id][0]
        self.assertTrue(delivery_line, "No line for delivery 1")
        self.assertFalse(delivery_line["replenishment_filled"])
        delivery2_line = [l for l in lines if l["document_out"]["id"] == delivery2.id][
            0
        ]
        self.assertTrue(delivery2_line, "No line for delivery 2")
        self.assertTrue(delivery2_line["replenishment_filled"])

    def test_report_forecast_9_delivery_to_receipt_link_over_received(self):
        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 300
        receipt = receipt_form.save()
        receipt.move_ids[0].write(
            {
                "move_dest_ids": [(4, delivery2.move_ids[0].id)],
            }
        )
        receipt.action_confirm()

        self.assertEqual(delivery.move_ids.forecast_availability, 100)
        self.assertEqual(delivery2.move_ids.forecast_availability, 200)
        self.assertEqual(delivery.move_ids.date_planned_forecast, receipt.move_ids.date)
        self.assertEqual(
            delivery2.move_ids.date_planned_forecast, receipt.move_ids.date
        )

        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )

        self.assertEqual(len(lines), 2, "Only 2 lines")
        delivery_line = [l for l in lines if l["document_out"]["id"] == delivery.id][0]
        self.assertTrue(delivery_line, "No line for delivery 1")
        self.assertTrue(delivery_line["replenishment_filled"])
        delivery2_line = [l for l in lines if l["document_out"]["id"] == delivery2.id][
            0
        ]
        self.assertTrue(delivery2_line, "No line for delivery 2")
        self.assertTrue(delivery2_line["replenishment_filled"])

    def test_report_forecast_10_report_line_corresponding_to_picking_highlighted(self):
        delivery_form = Form(self.env["stock.picking"])
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.date_planned = date.today()
        with delivery_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 200
        delivery1 = delivery_form.save()
        delivery1.action_confirm()

        date_planned1 = datetime.now() + timedelta(days=1)
        receipt_form = Form(self.env["stock.picking"])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = date_planned1
        with receipt_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 150
        receipt1 = receipt_form.save()
        receipt1.action_confirm()
        self.assertEqual(delivery1.move_ids.forecast_availability, -50.0)

        date_planned2 = datetime.now() + timedelta(days=3)
        receipt_form = Form(self.env["stock.picking"])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = date_planned2
        with receipt_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 50
        receipt2 = receipt_form.save()
        receipt2.action_confirm()

        delivery1.move_ids._compute_forecast_information()
        self.assertEqual(delivery1.move_ids.forecast_availability, 200)
        self.assertEqual(delivery1.move_ids.date_planned_forecast, date_planned2)

        receipt2.move_ids.quantity = receipt2.move_ids.product_uom_qty
        receipt2.move_ids.picked = True
        receipt2.button_validate()
        delivery1.move_ids._compute_forecast_information()
        self.assertEqual(delivery1.move_ids.forecast_availability, 200)
        self.assertEqual(delivery1.move_ids.date_planned_forecast, date_planned1)

        delivery2 = delivery1.copy()
        delivery2_form = Form(delivery2)
        delivery2_form.date_planned = datetime.now() + timedelta(days=1)
        delivery2 = delivery2_form.save()
        delivery2.action_confirm()
        delivery2.move_ids.quantity = delivery1.move_ids.quantity
        delivery2.action_unreserve()
        self.assertEqual(delivery2.move_ids.forecast_availability, -200)

        for picking in [delivery1, delivery2, receipt1, receipt2]:
            context = picking.move_ids[0].action_product_forecast_report()["context"]
            _, _, lines = self.get_report_forecast(
                product_template_ids=self.product_template.ids, context=context
            )
            for line in lines:
                if (
                    line["document_in"] and picking.id == line["document_in"]["id"]
                ) or (
                    line["document_out"] and picking.id == line["document_out"]["id"]
                ):
                    self.assertTrue(
                        line["is_matched"],
                        "The corresponding picking should be matched in the forecast report.",
                    )
                else:
                    self.assertFalse(
                        line["is_matched"],
                        "A line of the forecast report not linked to the picking shoud not be matched.",
                    )

    def test_report_forecast_11_non_reserved_order(self):
        picking_type_manual = self.picking_type_out.copy()
        picking_type_by_date = picking_type_manual.copy()
        picking_type_at_confirm = picking_type_manual.copy()
        picking_type_manual.reservation_method = "manual"
        picking_type_manual.sequence_code = "manual"
        picking_type_by_date.reservation_method = "by_date"
        picking_type_by_date.sequence_code = "by"
        picking_type_by_date.reservation_days_before = "6"
        picking_type_by_date.reservation_days_before_priority = "4"
        picking_type_at_confirm.reservation_method = "at_confirm"
        picking_type_at_confirm.sequence_code = "confirm"

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_manual
        delivery_form.date_planned = datetime.now() - timedelta(days=10)
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_manual = delivery_form.save()
        delivery_manual.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_by_date
        delivery_form.date_planned = datetime.now() + timedelta(days=5)
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_by_date = delivery_form.save()
        delivery_by_date.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_by_date
        delivery_form.date_planned = datetime.now() + timedelta(days=5)
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_by_date_priority = delivery_form.save()
        delivery_form.priority = "1"
        delivery_by_date_priority = delivery_form.save()
        delivery_by_date_priority.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_at_confirm
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_at_confirm = delivery_form.save()
        delivery_at_confirm.action_confirm()

        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        self.assertEqual(len(lines), 4, "The report must have 4 lines.")
        self.assertEqual(lines[0]["document_out"]["id"], delivery_at_confirm.id)
        self.assertEqual(lines[1]["document_out"]["id"], delivery_by_date.id)
        self.assertEqual(lines[2]["document_out"]["id"], delivery_by_date_priority.id)
        self.assertEqual(lines[3]["document_out"]["id"], delivery_manual.id)

        all_delivery = (
            delivery_by_date
            | delivery_at_confirm
            | delivery_by_date_priority
            | delivery_manual
        )
        self.assertEqual(
            all_delivery.move_ids.mapped("forecast_availability"),
            [-3.0, -3.0, -3.0, -3.0],
        )

        receipt_form = Form(self.env["stock.picking"])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.date_planned = date.today() + timedelta(days=1)
        with receipt_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 6
        receipt1 = receipt_form.save()
        receipt1.action_confirm()

        self.assertEqual(
            all_delivery.move_ids.mapped("forecast_availability"), [3, 3, -3.0, -3.0]
        )

    def test_report_forecast_12_reserved_transit(self):
        grp_multi_loc = self.env.ref("stock.group_stock_multi_locations")
        grp_multi_routes = self.env.ref("stock.group_adv_location")
        self.env.user.write({"group_ids": [(4, grp_multi_loc.id)]})
        self.env.user.write({"group_ids": [(4, grp_multi_routes.id)]})
        warehouse = self.env.ref("stock.warehouse0")
        warehouse.reception_steps = "two_steps"
        outgoing = Form(self.env["stock.picking"])
        outgoing.picking_type_id = self.picking_type_out
        with outgoing.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 2
        outgoing = outgoing.save()
        outgoing.action_confirm()
        incoming = Form(self.env["stock.picking"])
        incoming.picking_type_id = self.picking_type_in
        with incoming.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 2
        incoming = incoming.save()
        incoming.action_confirm()
        incoming.move_ids.picked = True
        incoming.button_validate()
        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(bool(lines[0]["move_out"]), True)
        self.assertEqual(lines[0]["in_transit"], True)

    def test_report_forecast_13_availability_from_sublocations(self):
        stock_location = self.env.ref("stock.warehouse0").lot_stock_id
        sublocation = self.env["stock.location"].create(
            {
                "name": "Warehouse0 / Sublocation",
                "barcode": "TEST_BARCODE_LOCATION",
                "location_id": stock_location.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product, sublocation, 10.0
        )
        delivery_form = Form(self.env["stock.picking"])
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.partner_id = self.partner
        with delivery_form.move_ids.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 3
        delivery = delivery_form.save()
        delivery.action_confirm()
        delivery.action_unreserve()
        self.assertRecordValues(
            delivery.move_ids,
            [
                {
                    "product_uom_qty": 3.0,
                    "location_id": stock_location.id,
                    "quantity": 0.0,
                    "forecast_availability": 3.0,
                }
            ],
        )
        with Form(delivery) as delivery_form:
            delivery_form.location_id = sublocation
        self.assertRecordValues(
            delivery.move_ids,
            [
                {
                    "product_uom_qty": 3.0,
                    "location_id": sublocation.id,
                    "quantity": 0.0,
                    "forecast_availability": 3.0,
                }
            ],
        )
        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product.product_tmpl_id.ids
        )
        self.assertEqual(len(lines), 2)
        picking_line = next(filter(lambda line: line.get("document_out"), lines))
        self.assertEqual(
            (
                picking_line["quantity"],
                picking_line["replenishment_filled"],
                picking_line["document_out"]["id"],
            ),
            (3.0, True, delivery.id),
        )
        stock_line = next(filter(lambda line: not line.get("document_out"), lines))
        self.assertEqual(
            (stock_line["quantity"], stock_line["replenishment_filled"]), (7.0, True)
        )

    def test_report_forecast_14_ongoing_multi_step_delivery(self):
        customer_loc, __ = self.env["stock.warehouse"]._get_partner_locations()
        self.wh_2.write({"delivery_steps": "pick_ship"})

        move_pick = self.env["stock.move"].create(
            {
                "picking_type_id": self.wh_2.pick_type_id.id,
                "location_id": self.wh_2.lot_stock_id.id,
                "location_final_id": customer_loc.id,
                "product_id": self.product1.id,
                "product_uom_qty": 5.0,
            }
        )
        move_pick._action_confirm()
        _, _, lines = self.get_report_forecast(
            product_template_ids=self.product1.product_tmpl_id.ids,
            context={"warehouse_id": self.wh_2.id},
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["move_out"]["id"], move_pick.id)

    def test_report_reception_1_one_receipt(self):
        product2 = self.env["product.product"].create(
            {
                "name": "Extra Product",
                "is_storable": True,
            }
        )

        product3 = self.env["product.product"].create(
            {
                "name": "Unpopular Product",
                "is_storable": True,
            }
        )

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = product2
            move_line.product_uom_qty = 10
        delivery1 = delivery_form.save()
        delivery1.action_confirm()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 15
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = product2
            move_line.product_uom_qty = 5
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = product3
            move_line.product_uom_qty = 5
        receipt = receipt_form.save()

        report = self.env["report.stock.report_reception"]
        report_values = report._get_report_values(docids=[receipt.id])
        sources_to_lines = report_values["sources_to_lines"]
        self.assertEqual(
            len(sources_to_lines),
            2,
            "The report has wrong number of outgoing pickings.",
        )
        all_lines = []
        for lines in sources_to_lines.values():
            for line in lines:
                self.assertFalse(
                    line["is_qty_assignable"],
                    "The receipt IS DRAFT => its move quantities ARE NOT available to assign.",
                )
                all_lines.append(line)
        self.assertEqual(
            len(all_lines), 3, "The report has wrong number of outgoing moves."
        )
        self.assertEqual(
            all_lines[0]["quantity"], 5, "The first move has wrong incoming qty."
        )
        self.assertEqual(
            all_lines[0]["product"]["id"],
            self.product.id,
            "The first move has wrong incoming product to assign.",
        )
        self.assertEqual(
            all_lines[1]["quantity"], 5, "The second move has wrong incoming qty."
        )
        self.assertEqual(
            all_lines[1]["product"]["id"],
            product2.id,
            "The second move has wrong incoming product to assign.",
        )
        self.assertEqual(
            all_lines[2]["quantity"], 2, "The last move has wrong incoming qty."
        )
        self.assertEqual(
            all_lines[2]["product"]["id"],
            self.product.id,
            "The third move has wrong incoming product to assign.",
        )

        receipt.action_confirm()
        for move in receipt.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        receipt.button_validate()
        report_values = report._get_report_values(docids=[receipt.id])

        sources_to_lines = report_values["sources_to_lines"]
        all_lines = []
        move_ids = []
        qtys = []
        in_ids = []
        for lines in sources_to_lines.values():
            for line in lines:
                self.assertTrue(
                    line["is_qty_assignable"],
                    "The receipt IS DONE => all of its move quantities ARE assignable",
                )
                all_lines.append(line)
                move_ids.append(line["move_out"].id)
                qtys.append(line["quantity"])
                in_ids += line["move_ins"]
        self.assertEqual(
            len(all_lines), 3, "The report has wrong number of outgoing moves."
        )
        self.assertEqual(
            all_lines[0]["quantity"],
            5,
            "The first move has wrong incoming qty to reserve.",
        )
        self.assertEqual(
            all_lines[0]["product"]["id"],
            self.product.id,
            "The first move has wrong product to reserve.",
        )
        self.assertEqual(
            all_lines[1]["quantity"],
            5,
            "The second move has wrong incoming qty to reserve.",
        )
        self.assertEqual(
            all_lines[1]["product"]["id"],
            product2.id,
            "The second move has wrong product to reserve.",
        )
        self.assertEqual(
            all_lines[2]["quantity"],
            2,
            "The last move has wrong incoming qty to reserve.",
        )
        self.assertEqual(
            all_lines[2]["product"]["id"],
            self.product.id,
            "The third move has wrong product to reserve.",
        )

        report.action_assign(move_ids, qtys, in_ids)
        self.assertEqual(
            len(receipt.move_ids[0].move_dest_ids.ids),
            2,
            "Demand qty of first and last moves should now be linked to incoming.",
        )
        self.assertEqual(
            len(receipt.move_ids[1].move_dest_ids.ids),
            1,
            "Demand qty of second move should now be linked to incoming.",
        )
        self.assertEqual(
            len(receipt.move_ids[2].move_dest_ids.ids),
            0,
            "product3 should have no moves linked to it.",
        )
        self.assertEqual(
            len(delivery1.move_ids.filtered(lambda m: m.product_id == product2)),
            2,
            "product2 outgoing move should be split between linked and non-linked quantities.",
        )

    def test_report_reception_2_two_receipts(self):
        qty_outgoing = 100
        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_outgoing
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt1_qty = 5
        receipt2_qty = 3
        qty_incoming = receipt1_qty + receipt2_qty
        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = receipt1_qty
        receipt1 = receipt_form.save()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = receipt2_qty
        receipt2 = receipt_form.save()

        report = self.env["report.stock.report_reception"]
        report_values = report._get_report_values(docids=[receipt1.id, receipt2.id])
        self.assertEqual(
            len(report_values["docs"]),
            2,
            "There should be 2 receipts to assign from in this report",
        )
        sources_to_lines = report_values["sources_to_lines"]
        self.assertEqual(
            len(sources_to_lines),
            1,
            "The report has wrong number of outgoing pickings.",
        )
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(
            len(all_lines), 1, "The report has wrong number of outgoing move lines."
        )
        self.assertFalse(
            all_lines[0]["is_qty_assignable"],
            "The receipt IS NOT done => its move quantities ARE NOT available to reserve (i.e. done).",
        )
        self.assertEqual(
            all_lines[0]["quantity"], 8, "The move has wrong incoming qty."
        )

        receipt1.action_confirm()
        for move in receipt1.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        report_values = report._get_report_values(docids=[receipt1.id, receipt2.id])

        sources_to_lines = report_values["sources_to_lines"]
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(
            len(all_lines),
            2,
            "The report has wrong number of lines (1 assignable + 1 not).",
        )
        self.assertEqual(
            all_lines[0]["quantity"],
            receipt1_qty,
            "The first move has wrong incoming qty to assign.",
        )
        self.assertTrue(
            all_lines[0]["is_qty_assignable"],
            "1 receipt is confirmed => should have 1 reservable move.",
        )
        self.assertEqual(
            all_lines[1]["quantity"],
            receipt2_qty,
            "The second move has wrong (expected) incoming qty.",
        )
        self.assertFalse(
            all_lines[1]["is_qty_assignable"],
            "1 receipt is draft => should have 1 non-assignable move.",
        )

        receipt2.action_confirm()
        report_values = report._get_report_values(docids=[receipt1.id, receipt2.id])
        sources_to_lines = report_values["sources_to_lines"]
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(
            len(all_lines),
            1,
            "The report has wrong number of lines (1 outgoing move they are assignable to).",
        )
        self.assertEqual(
            all_lines[0]["quantity"],
            qty_incoming,
            "The total amount of incoming qty to assign should be receipt1 + receipt2's qties.",
        )
        self.assertTrue(
            all_lines[0]["is_qty_assignable"],
            "receipts are confirmed, incoming moves should be assignable.",
        )
        report.action_assign(
            delivery.move_ids.ids, [qty_incoming], (receipt1 | receipt2).move_ids.ids
        )
        mto_move = delivery.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_move = delivery.move_ids - mto_move
        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            len(non_mto_move),
            1,
            "Remaining not-assigned outgoing qty should have split into separate move",
        )
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Incorrect quantity split for MTO move",
        )
        self.assertEqual(mto_move.state, "waiting", "MTO move state not correctly set")
        report.action_unassign([mto_move.id], receipt2_qty, receipt2.move_ids.ids)
        mto_move = delivery.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_moves = delivery.move_ids - mto_move
        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            len(non_mto_moves),
            2,
            "Original split not-assigned outgoing qty should still exist + new move of unassigned qty",
        )
        self.assertEqual(
            mto_move.product_uom_qty,
            receipt1_qty,
            "Incorrect quantity split for remaining MTO move qty",
        )
        self.assertEqual(
            mto_move.state, "waiting", "MTO move state shouldn't have changed"
        )

        receipt1.button_validate()
        reason = report._get_report_values(docids=[receipt1.id, receipt2.id])["reason"]
        self.assertEqual(
            reason,
            "This report cannot be used for done and not done %s at the same time"
            % report._get_doc_types_label(),
            "empty report reason not shown",
        )

        receipt2.button_validate()
        delivery.action_cancel()
        delivery2 = delivery.copy()
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": qty_outgoing,
            }
        ).action_apply_inventory()
        delivery2.action_confirm()
        self.assertEqual(
            delivery2.move_ids.quantity,
            qty_outgoing,
            "Delivery move should already be reserved",
        )
        report.action_assign(
            delivery2.move_ids.ids, [qty_incoming], (receipt1 | receipt2).move_ids.ids
        )
        mto_move = delivery2.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_move = delivery2.move_ids - mto_move
        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            len(non_mto_move),
            1,
            "Remaining not-assigned outgoing qty should have split into separate move",
        )
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Incorrect quantity split for MTO move",
        )
        self.assertEqual(
            mto_move.state, "assigned", "MTO move should still be reserved"
        )
        report.action_unassign([mto_move.id], receipt2_qty, receipt2.move_ids.ids)
        mto_move = delivery2.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_moves = delivery2.move_ids - mto_move
        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            len(non_mto_moves),
            2,
            "Original split not-assigned outgoing qty should still exist + new move of unassigned qty",
        )
        self.assertEqual(
            mto_move.product_uom_qty,
            receipt1_qty,
            "Incorrect quantity split for remaining MTO move qty",
        )
        self.assertEqual(
            mto_move.quantity,
            receipt1_qty,
            "Incorrect reserved amount split for remaining MTO move qty",
        )
        self.assertEqual(
            mto_move.state, "assigned", "MTO move state shouldn't have changed"
        )
        total_non_mto_qty = sum(move.quantity for move in non_mto_moves)
        self.assertEqual(
            total_non_mto_qty,
            qty_outgoing - (receipt1_qty + receipt2_qty),
            "Unassigned move should be also unreserved",
        )

    def test_report_reception_3_multiwarehouse(self):
        wh_2 = self.env["stock.warehouse"].create(
            {
                "name": "Other Warehouse",
                "code": "OTHER",
            }
        )
        picking_type_out_2 = self.env["stock.picking.type"].search(
            [
                ("code", "=", "outgoing"),
                ("warehouse_id", "=", wh_2.id),
            ]
        )

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_out_2
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.quantity = 15
        receipt = receipt_form.save()

        report = self.env["report.stock.report_reception"]
        report_values = report._get_report_values(docids=[receipt.id])
        self.assertEqual(
            len(report_values["sources_to_lines"]),
            0,
            "The receipt and delivery are in different warehouses => no moves to link to should be found.",
        )

    def test_report_reception_5_move_splitting(self):
        qty_incoming = 4
        qty_outgoing = 10
        qty_in_stock = qty_outgoing - qty_incoming
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": qty_in_stock,
            }
        ).action_apply_inventory()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_outgoing
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_incoming
        receipt = receipt_form.save()
        receipt.action_confirm()

        self.assertEqual(len(delivery.move_ids), 1)
        report = self.env["report.stock.report_reception"]

        report.action_assign(
            delivery.move_ids.ids, [qty_incoming], receipt.move_ids.ids
        )
        mto_move = delivery.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_move = delivery.move_ids - mto_move

        self.assertEqual(
            len(delivery.move_ids),
            2,
            "Delivery moves should have split into assigned + not assigned",
        )
        self.assertEqual(
            len(delivery.move_ids.mapped("move_orig_ids")),
            1,
            "Only 1 delivery + 1 receipt move should be assigned",
        )
        self.assertEqual(
            len(receipt.move_ids.mapped("move_dest_ids")),
            1,
            "Receipt move should remain unsplit",
        )

        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Incorrect quantity split for MTO move",
        )
        self.assertEqual(
            mto_move.quantity,
            0,
            "Receipt is not done => assigned move can't have a reserved qty",
        )
        self.assertEqual(mto_move.state, "waiting", "MTO move state not correctly set")

        self.assertEqual(
            non_mto_move.product_uom_qty,
            qty_outgoing - qty_incoming,
            "Incorrect quantity split for non-MTO move",
        )
        self.assertEqual(
            non_mto_move.quantity,
            qty_in_stock,
            "Reserved qty not correctly linked to non-MTO move",
        )
        self.assertEqual(
            non_mto_move.state,
            "assigned",
            "Fully reserved move has not correctly set state",
        )

        report.action_unassign([mto_move.id], qty_incoming, receipt.move_ids.ids)
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Move quantities should be unchanged",
        )
        self.assertEqual(
            mto_move.procure_method,
            "make_to_stock",
            "Procure method not correctly reset",
        )
        self.assertEqual(
            mto_move.state,
            "confirmed",
            "Move state not correctly reset (to non-MTO state)",
        )

    def test_report_reception_6_backorders(self):
        qty_incoming = 10
        qty_outgoing = 8
        orig_incoming_quantity = 4

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_outgoing
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_incoming
        receipt = receipt_form.save()
        receipt.action_confirm()

        report = self.env["report.stock.report_reception"]
        report.action_assign(
            delivery.move_ids.ids, [qty_outgoing], receipt.move_ids.ids
        )
        self.assertEqual(
            receipt.move_ids.move_dest_ids.ids,
            delivery.move_ids.ids,
            "Link between receipt and delivery moves should have been made",
        )

        for move in receipt.move_ids:
            move.quantity = orig_incoming_quantity
        receipt.move_ids.picked = True
        Form.from_action(self.env, receipt.button_validate()).save().process()
        backorder = self.env["stock.picking"].search(
            [("backorder_id", "=", receipt.id)]
        )

        self.assertEqual(
            receipt.move_ids.move_dest_ids,
            backorder.move_ids.move_dest_ids,
            "Backorder should have copied link to delivery move",
        )
        report_values = report._get_report_values(docids=[backorder.id])
        sources_to_lines = report_values["sources_to_lines"]
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(
            len(all_lines), 1, "The report has wrong number of outgoing moves."
        )
        self.assertEqual(
            all_lines[0]["quantity"],
            qty_incoming - orig_incoming_quantity,
            "The report doesn't have the correct qty assigned.",
        )

        report.action_unassign(
            delivery.move_ids.ids, qty_outgoing, backorder.move_ids.ids
        )
        self.assertEqual(
            len(delivery.move_ids),
            2,
            "The delivery should have split its reserved qty from the original move",
        )
        reserved_move = receipt.move_ids.move_dest_ids
        self.assertEqual(
            len(reserved_move),
            1,
            "Move w/reserved qty should have full demand reserved",
        )
        self.assertEqual(
            reserved_move.state,
            "assigned",
            "Move w/reserved qty should have full demand reserved",
        )
        self.assertEqual(
            reserved_move.product_uom_qty,
            orig_incoming_quantity,
            "Done amount in original receipt should be amount demanded/reserved in delivery still with a link",
        )
        report_values = report._get_report_values(docids=[backorder.id])
        sources_to_lines = report_values["sources_to_lines"]
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(
            len(all_lines),
            1,
            "The report should only contain the remaining non-reserved move",
        )
        self.assertEqual(
            all_lines[0]["quantity"],
            qty_outgoing - orig_incoming_quantity,
            "The report doesn't have the correct qty to assign",
        )

        report.action_assign(
            (delivery.move_ids - reserved_move).ids,
            [qty_outgoing - orig_incoming_quantity],
            backorder.move_ids.ids,
        )
        for move in backorder.move_ids:
            move.quantity = qty_incoming - orig_incoming_quantity
        backorder.move_ids.picked = True
        backorder.button_validate()
        for move in delivery.move_ids:
            self.assertEqual(
                move.state,
                "assigned",
                "All delivery moves should be fully reserved now",
            )

    def test_report_reception_7_done_receipt(self):
        qty_incoming = 4
        qty_outgoing = 10
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "location_id": self.stock_location.id,
                "inventory_quantity": qty_outgoing,
            }
        ).action_apply_inventory()

        delivery_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_outgoing
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt_form = Form(
            self.env["stock.picking"], view="stock.view_stock_picking_form"
        )
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = qty_incoming
        receipt = receipt_form.save()
        receipt.action_confirm()
        receipt.button_validate()

        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(
            delivery.move_ids.quantity,
            qty_outgoing,
            "Delivery move should already be reserved",
        )
        report = self.env["report.stock.report_reception"]

        report.action_assign(
            delivery.move_ids.ids, [qty_incoming], receipt.move_ids.ids
        )
        mto_move = delivery.move_ids.filtered(
            lambda m: m.procure_method == "make_to_order"
        )
        non_mto_move = delivery.move_ids - mto_move

        self.assertEqual(
            len(delivery.move_ids),
            2,
            "Delivery moves should have split into assigned + not assigned",
        )
        self.assertEqual(
            len(delivery.move_ids.move_orig_ids),
            1,
            "Only 1 delivery + 1 receipt move should be assigned",
        )
        self.assertEqual(
            len(receipt.move_ids.move_dest_ids), 1, "Receipt move should remain unsplit"
        )

        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Incorrect quantity split for MTO move",
        )
        self.assertEqual(
            mto_move.quantity,
            qty_incoming,
            "Receipt IS done => assigned pre-reserved move reserved_qty = assigned receipt move qty",
        )
        self.assertEqual(mto_move.state, "assigned", "MTO move state not correctly set")

        self.assertEqual(
            non_mto_move.product_uom_qty,
            qty_outgoing - qty_incoming,
            "Incorrect quantity split for non-MTO move",
        )
        self.assertEqual(
            non_mto_move.quantity,
            qty_outgoing - qty_incoming,
            "Remaining reserved qty not correctly linked to non-MTO move",
        )
        self.assertEqual(
            non_mto_move.state,
            "assigned",
            "Remaining non-MTO reserved move should stay reserved",
        )

        report.action_unassign([mto_move.id], qty_incoming, receipt.move_ids.ids)
        self.assertEqual(
            mto_move.product_uom_qty,
            qty_incoming,
            "Move quantities should be unchanged",
        )
        self.assertEqual(
            mto_move.procure_method,
            "make_to_stock",
            "Procure method not correctly reset",
        )
        self.assertEqual(
            mto_move.state,
            "confirmed",
            "Unassigning receipt move should also unreserve the out move",
        )

    def test_report_reception_immediate_transfer(self):
        Report = self.env["report.stock.report_reception"]

        planned_delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )
        planned_delivery.action_confirm()

        immediate_receipt_transfer = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        self.env["stock.move.line"].create(
            {
                "picking_id": immediate_receipt_transfer.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": self.product.id,
                "quantity": 1,
            }
        )

        sources_to_lines = Report._get_report_values(
            docids=[immediate_receipt_transfer.id]
        )["sources_to_lines"]
        for lines in sources_to_lines.values():
            for line in lines:
                self.assertFalse(line["is_qty_assignable"])

        immediate_receipt_transfer.button_validate()
        out_move = planned_delivery.move_ids
        in_move = immediate_receipt_transfer.move_ids

        (sources_lines_items,) = Report._get_report_values(
            docids=[immediate_receipt_transfer.id]
        )["sources_to_lines"].items()
        sources, lines = sources_lines_items
        ((source,),) = sources
        self.assertEqual(source, planned_delivery)
        self.assertEqual(lines[0]["quantity"], out_move.quantity)

        Report.action_assign(out_move.ids, [out_move.quantity], [in_move.ids])
        self.assertEqual(out_move.procure_method, "make_to_order")

        Report.action_unassign(out_move.id, out_move.quantity, in_move.ids)
        self.assertEqual(out_move.procure_method, "make_to_stock")

    def test_report_stock_lot_customer_simple_delivery(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        out_type = self.env.ref("stock.picking_type_out")

        sn = self.env["stock.lot"].create(
            {"name": "supersn", "product_id": self.serial_product.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            self.serial_product, stock_location, quantity=1, lot_id=sn
        )

        delivery = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": out_type.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.serial_product.id,
                            "product_uom_qty": 1,
                            "location_id": stock_location.id,
                            "location_dest_id": customer_location.id,
                        }
                    )
                ],
            }
        )
        delivery.action_confirm()
        delivery.button_validate()

        action_view_stock_serial_domain = self.partner.action_view_stock_serial()[
            "domain"
        ]
        customer_lots = self.env["stock.lot"].search(action_view_stock_serial_domain)
        self.assertEqual(customer_lots, sn)

    def test_partner_lot_report_sml_without_picking(self):
        stock_location = self.env.ref("stock.stock_location_stock")
        customer_location = self.env.ref("stock.stock_location_customers")
        out_type = self.env.ref("stock.picking_type_out")

        self.product.is_storable = False
        delivery = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": out_type.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": stock_location.id,
                            "location_dest_id": customer_location.id,
                        }
                    )
                ],
            }
        )
        delivery.action_confirm()

        sn = self.env["stock.lot"].create(
            {"name": "supersn", "product_id": self.serial_product.id}
        )
        delivery.move_ids = [
            Command.create(
                {
                    "product_id": self.serial_product.id,
                    "product_uom_qty": 1,
                    "location_id": stock_location.id,
                    "location_dest_id": customer_location.id,
                    "move_line_ids": [
                        Command.create(
                            {
                                "product_id": self.serial_product.id,
                                "quantity": 1,
                                "lot_id": sn.id,
                            }
                        )
                    ],
                }
            )
        ]
        delivery.button_validate()

        action_view_stock_serial_domain = self.partner.action_view_stock_serial()[
            "domain"
        ]
        customer_lots = self.env["stock.lot"].search(action_view_stock_serial_domain)
        self.assertEqual(customer_lots, sn)

    def test_stock_reception_partial_available_move_assign(self):
        warehouse_1 = self.env.ref("stock.warehouse0")
        shelf1 = self.env["stock.location"].create(
            {
                "name": "Shelf 1",
                "location_id": warehouse_1.lot_stock_id.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(self.product, shelf1, 2.0)
        picking_out = self.env["stock.picking"].create(
            {
                "picking_type_id": self.ref("stock.picking_type_out"),
                "location_id": warehouse_1.lot_stock_id.id,
                "location_dest_id": self.ref("stock.stock_location_customers"),
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.ref("uom.product_uom_unit"),
                            "product_uom_qty": 3.0,
                        }
                    )
                ],
            }
        )
        out_move = picking_out.move_ids
        self.env.ref("stock.picking_type_out").reservation_method = "at_confirm"
        picking_out.action_confirm()
        picking_in = self.env["stock.picking"].create(
            {
                "picking_type_id": self.ref("stock.picking_type_in"),
                "location_id": self.ref("stock.stock_location_suppliers"),
                "location_dest_id": warehouse_1.lot_stock_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.ref("uom.product_uom_unit"),
                            "product_uom_qty": 1.0,
                        }
                    )
                ],
            }
        )
        picking_in.action_confirm()
        picking_in.button_validate()
        self.env["report.stock.report_reception"].action_assign(
            out_move.ids, [1.0], picking_in.move_ids.ids
        )
        self.assertEqual(picking_out.move_ids.mapped("quantity"), [1.0, 2.0])
        self.env["report.stock.report_reception"].action_unassign(
            out_move.id, 1, picking_in.move_ids.ids
        )
        self.assertEqual(picking_out.move_ids.mapped("quantity"), [0.0, 2.0])
        self.env["report.stock.report_reception"].action_assign(
            out_move.ids, [1.0], picking_in.move_ids.ids
        )
        self.assertEqual(picking_out.move_ids.mapped("quantity"), [1.0, 2.0])

    def test_report_reception_assign_all_with_expected_line(self):
        warehouse = self.env.ref("stock.warehouse0")
        supplier_loc = self.ref("stock.stock_location_suppliers")
        stock_loc = warehouse.lot_stock_id.id

        def create_receipt(qty):
            return self.env["stock.picking"].create(
                {
                    "picking_type_id": self.ref("stock.picking_type_in"),
                    "location_id": supplier_loc,
                    "location_dest_id": stock_loc,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_id": self.ref("uom.product_uom_unit"),
                                "product_uom_qty": qty,
                            }
                        )
                    ],
                }
            )

        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": self.ref("stock.picking_type_out"),
                "location_id": stock_loc,
                "location_dest_id": self.ref("stock.stock_location_customers"),
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.ref("uom.product_uom_unit"),
                            "product_uom_qty": 10.0,
                        }
                    )
                ],
            }
        )
        delivery.action_confirm()

        receipt_confirmed = create_receipt(6.0)
        receipt_confirmed.action_confirm()
        receipt_draft = create_receipt(10.0)

        report = self.env["report.stock.report_reception"]
        data = report.get_report_data(
            [receipt_confirmed.id, receipt_draft.id], {"report_type": "html"}
        )
        lines = [
            line
            for source_lines in data["sources_to_lines"].values()
            for line in source_lines
        ]
        self.assertEqual(len(lines), 2)
        assignable = next(line for line in lines if line["is_qty_assignable"])
        expected = next(line for line in lines if not line["is_qty_assignable"])
        self.assertEqual(assignable["quantity"], 6.0)
        self.assertEqual(expected["quantity"], 4.0)
        self.assertFalse(expected["move_ins"])
        self.assertEqual(assignable["move_out_id"], expected["move_out_id"])

        move_ids, qtys, in_ids = [], [], []
        for line in lines:
            if line["is_assigned"]:
                continue
            move_ids.append(line["move_out_id"])
            qtys.append(line["quantity"])
            in_ids.append(line["move_ins"])
        self.assertIn(False, in_ids, "the expected line must contribute a False entry")

        report.action_assign(move_ids, qtys, in_ids)

        linked_out = receipt_confirmed.move_ids.move_dest_ids
        self.assertTrue(
            linked_out,
            "the confirmed receipt should have been linked to the delivery",
        )
        self.assertEqual(linked_out.procure_method, "make_to_order")
        self.assertEqual(linked_out.product_qty, 6.0)
        self.assertEqual(len(delivery.move_ids), 2)


class TestPickingPrint(TestReportsCommon):
    def _picking(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "partner_id": self.partner.id,
            }
        )

    def test_rendering_the_picking_operations_report_marks_the_picking_printed(self):
        picking = self._picking()
        self.assertFalse(picking.printed)
        self.env["ir.actions.report"]._render_qweb_pdf(
            "stock.action_report_picking", picking.ids
        )
        self.assertTrue(picking.printed)

    def test_rendering_the_delivery_slip_leaves_the_picking_unprinted(self):
        picking = self._picking()
        self.env["ir.actions.report"]._render_qweb_pdf(
            "stock.action_report_delivery", picking.ids
        )
        self.assertFalse(picking.printed)

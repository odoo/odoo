import io

from PIL import Image

from odoo import http
from odoo.fields import Command
from odoo.http import request
from odoo.tests import HttpCase

from odoo.addons.printer.models.ir_actions_report import thermal_printer_format
from odoo.addons.stock.controllers.main import StockReportController
from odoo.addons.stock.tests.common import TestStockCommon


class TestPrinterTour(TestStockCommon, HttpCase):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["printer.printer"].create(
            [
                {
                    "name": "Test Zebra Printer",
                    "type": "zpl",
                    "ip_address": "127.0.0.1:8069",
                    "report_ids": [
                        Command.link(cls.env.ref("product.report_product_template_label_zpl").id),
                    ],
                },
                {
                    "name": "Test Epson Printer",
                    "type": "epos",
                    "ip_address": "127.0.0.1:8069",
                    "report_ids": [
                        Command.link(
                            cls.env.ref(
                                "stock_delivery.action_report_shipping_labels",
                            ).id,
                        ),
                    ],
                },
            ],
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
            },
        )

    def test_print_label_zpl(self):
        """test that the simulated ``/pstprnt`` controller
        receives the print job with the correct content
        when printing a label with a ZPL printer"""
        self.zebra_pstprnt_called = False

        def zebra_post_print(_):
            self.zebra_pstprnt_called = True
            body = request.httprequest.data
            actual_length = len(body)
            declared_length = request.httprequest.content_length

            self.assertEqual(
                declared_length,
                actual_length,
                f"Content-Length header ({declared_length}) does not match actual body length ({actual_length})",
            )
            zpl = body.decode("utf-8").strip()
            self.assertTrue(
                zpl.startswith("^XA"),
                f"ZPL does not start with ^XA: {zpl[:50]}",
            )
            self.assertTrue(
                zpl.endswith("^XZ"),
                f"ZPL does not end with ^XZ: {zpl[-50:]}",
            )
            self.assertIn(
                "Test Product",
                zpl,
                f"ZPL does not contain 'Test Product': {zpl}",
            )

        StockReportController.zebra_post_print = http.route(
            "/pstprnt",
            type="http",
            csrf=False,
            methods=["POST"],
        )(zebra_post_print)

        @self.addCleanup
        def _cleanup():
            del StockReportController.zebra_post_print

        self.start_tour("/odoo/products", "print_label_zebra_tour", login="admin")
        self.assertTrue(
            self.zebra_pstprnt_called,
            "The /pstprnt route was not called during the tour",
        )

    def test_print_label_epos(self):
        """test that the simulated ``/cgi-bin/epos/service.cgi`` controller
        receives the print job when printing a label with an EPOS printer"""
        self.epos_print_called = False

        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "outgoing")],
            limit=1,
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": self.partner_1.id,
                "product_id": self.product.id,
            },
        )

        buffer = io.BytesIO()
        Image.new("RGB", (100, 50), color=(255, 255, 255)).save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

        self.env["ir.attachment"].create(
            {
                "name": "LabelShipping.png",
                "type": "binary",
                "raw": png_bytes,
                "res_model": "stock.picking",
                "res_id": picking.id,
                "mimetype": "image/png",
            },
        )

        def epos_print(_, devid, **_kw):
            self.assertEqual(devid, "local_printer", "`devid` is set to `local_printer` by default on ePOS printers.")
            self.epos_print_called = True
            body = request.httprequest.data
            self.assertEqual(
                body,
                thermal_printer_format(png_bytes),
                "Body of the print request does not match the expected thermal printer format, "
                "ensure you called `thermal_printer_format` on the image data",
            )
            return request.make_response(
                '<response success="true" code=""/>',
                headers=[("Content-Type", "application/xml")],
            )

        StockReportController.epos_print = http.route(
            "/cgi-bin/epos/service.cgi",
            type="http",
            csrf=False,
            methods=["POST"],
        )(epos_print)

        @self.addCleanup
        def _cleanup():
            del StockReportController.epos_print

        self.start_tour(
            f"/odoo/inventory/{picking_type.id}/deliveries/{picking.id}",
            "print_label_epos_tour",
            login="admin",
        )
        self.assertTrue(
            self.epos_print_called,
            "The /cgi-bin/epos/service.cgi route was not called during the tour",
        )

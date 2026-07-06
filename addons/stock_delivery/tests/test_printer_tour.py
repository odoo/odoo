import io

from PIL import Image

from odoo.fields import Command
from odoo.tests import HttpCase

from odoo.addons.stock.tests.common import TestStockCommon


class TestPrinterTour(TestStockCommon, HttpCase):
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
        """test that the print job sent to the (mocked) ``/pstprnt`` endpoint
        has the correct content when printing a label with a ZPL printer."""
        self.start_tour(f"/odoo/products/{self.product.product_tmpl_id.id}", "print_label_zebra_tour", login="admin")

    def test_print_label_epos(self):
        """test that the simulated ``/cgi-bin/epos/service.cgi`` controller
        receives the print job when printing a label with an EPOS printer"""
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

        self.env["ir.attachment"].create(
            {
                "name": "LabelShipping.png",
                "type": "binary",
                "raw": buffer.getvalue(),
                "res_model": "stock.picking",
                "res_id": picking.id,
                "mimetype": "image/png",
            },
        )

        self.start_tour(
            f"/odoo/inventory/{picking_type.id}/deliveries/{picking.id}",
            "print_label_epos_tour",
            login="admin",
        )

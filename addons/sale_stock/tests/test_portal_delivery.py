from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPortalDeliveryReports(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env["res.partner"].create(
            {
                "name": "Portal delivery customer",
                "email": "portal.delivery@example.com",
            }
        )
        product = cls.env["product.product"].create(
            {
                "name": "Shippable widget",
                "type": "consu",
                "list_price": 10,
            }
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 2,
                        }
                    )
                ],
            }
        )
        cls.order.action_confirm()
        cls.picking = cls.order.picking_ids[:1]
        cls.token = cls.order._portal_get_or_create_token()

    def test_delivery_pdf_with_valid_token(self):
        self.assertTrue(self.picking)
        res = self.url_open(
            f"/my/picking/pdf/{self.picking.id}?access_token={self.token}",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")

    def test_delivery_pdf_without_token_is_denied(self):
        res = self.url_open(f"/my/picking/pdf/{self.picking.id}")
        self.assertIn(res.status_code, (403, 404))

    def test_delivery_pdf_with_wrong_token_is_denied(self):
        res = self.url_open(
            f"/my/picking/pdf/{self.picking.id}?access_token=forged-token",
        )
        self.assertIn(res.status_code, (403, 404))

    def test_return_label_pdf_with_valid_token(self):
        res = self.url_open(
            f"/my/picking/return/pdf/{self.picking.id}?access_token={self.token}",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")

    def test_missing_picking_is_not_found(self):
        res = self.url_open(
            f"/my/picking/pdf/99999999?access_token={self.token}",
        )
        self.assertIn(res.status_code, (403, 404))

    def test_delivery_pdf_for_picking_without_sale_order_is_denied(self):
        warehouse = self.order.warehouse_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )
        res = self.url_open(
            f"/my/picking/pdf/{picking.id}?access_token=forged-token",
        )
        self.assertIn(res.status_code, (403, 404))

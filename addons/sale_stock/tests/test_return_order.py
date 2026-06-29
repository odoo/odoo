# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from urllib.parse import urlencode

from odoo.tests import Form, HttpCase, tagged

from odoo.addons.sale_stock.tests.common import TestSaleStockCommon


@tagged("-at_install", "post_install")
class TestReturnOrderController(TestSaleStockCommon, HttpCase):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.allow_spontaneous_returns = True
        cls.portal_user = cls._create_new_portal_user()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.return_reason = cls.env.ref("sale_stock.return_reason_wrong_item")

    def setUp(self):
        super().setUp()
        self.sale_order = self._so_deliver(
            self.product_a, quantity=2, partner=self.portal_user.partner_id
        )
        self.sale_order._portal_ensure_token()

    def _download_return_label(self, sale_order=None, access_token=None):
        sale_order = sale_order or self.sale_order
        move = sale_order.order_line[:1].move_ids[:1]
        url_params = {
            "access_token": access_token or sale_order.access_token,
            "return_details": json.dumps({str(move.id): 1}),
            "return_reason_id": self.return_reason.id,
        }
        return self.url_open(
            f"/my/orders/{sale_order.id}/download_return_label?{urlencode(url_params)}",
            allow_redirects=False,
        )

    def _get_return_data(self, sale_order=None, access_token=None):
        sale_order = sale_order or self.sale_order
        return self.url_open(
            "/my/order/return_data",
            json={
                "params": {
                    "order_id": sale_order.id,
                    "access_token": access_token or sale_order.access_token,
                }
            },
        )

    def _make_return(self, picking, quantity_to_return):
        return_picking = picking._create_return()
        return_picking.move_ids[0].quantity = quantity_to_return
        return_picking.move_ids[0].picked = True
        return_picking._action_done()

    def test_return_data_returnable_line_structure(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        move = self.sale_order.order_line[:1].move_ids[:1]
        result = self._get_return_data().json()["result"]
        self.assertEqual(result["returnable_lines"], [{
            "move_id": move.id,
            "name": self.product_a.with_context(display_default_code=False).display_name,
            "picking_name": move.picking_id.name,
            "remaining_delivered_qty": 2,
            "lot_name": "",
            "price": 1.0,
            "product_id": self.product_a.id,
            "product_img_url": f"/web/image/product.product/{self.product_a.id}/image_128",
        }])

    def test_return_data_invalid_token_returns_error(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        private_sale_order = self._so_deliver(self.product_a, quantity=2, partner=self.partner_a)
        private_sale_order._portal_ensure_token()
        result = self._get_return_data(
            private_sale_order, access_token="invalid-token"
        ).json()["result"]
        self.assertIn("error", result)

    def test_download_label_invalid_token_redirects(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        private_sale_order = self._so_deliver(self.product_a, quantity=2, partner=self.partner_a)
        private_sale_order._portal_ensure_token()
        self.assertEqual(self._download_return_label(
            private_sale_order, access_token="invalid-token"
        ).status_code, 303)

    def test_partial_return_remaining_delivered_qty(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._make_return(self.sale_order.picking_ids, 1)
        returnable_lines = self._get_return_data().json()["result"]["returnable_lines"]
        self.assertEqual(returnable_lines[0]["remaining_delivered_qty"], 1)

    def test_fully_returned_line_is_not_returnable(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._make_return(self.sale_order.picking_ids, 2)
        returnable_lines = self._get_return_data().json()["result"]["returnable_lines"]
        self.assertFalse(returnable_lines)

    def test_multiple_pickings_are_returnable_separately(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        sale_order = self._so_deliver(
            self.product_a, quantity=5, picking=False, partner=self.portal_user.partner_id
        )
        sale_order._portal_ensure_token()
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 2, "picked": True})
        backorder_action = picking.button_validate()
        Form.from_action(self.env, backorder_action).save().process()
        backorder = picking.backorder_ids
        backorder.move_ids.write({"quantity": 3, "picked": True})
        backorder.button_validate()

        returnable_lines = self._get_return_data(sale_order).json()["result"]["returnable_lines"]
        self.assertEqual(
            {(ln["picking_name"], ln["remaining_delivered_qty"]) for ln in returnable_lines},
            {(picking.name, 2), (backorder.name, 3)},
        )

    def test_download_return_label_missing_params(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        move = self.sale_order.order_line[:1].move_ids[:1]
        cases = [
            {
                "access_token": self.sale_order.access_token,
                "return_reason_id": self.return_reason.id,
             },
            {
                "access_token": self.sale_order.access_token,
                "return_details": json.dumps({str(move.id): 1.0}),
            },
        ]

        for params in cases:
            with self.subTest(params=params):
                response = self.url_open(
                    f"/my/orders/{self.sale_order.id}/download_return_label?{urlencode(params)}",
                    allow_redirects=False,
                )
                self.assertEqual(response.status_code, 400)

    def test_download_label_logs_chatter_message(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._download_return_label()
        message = self.sale_order.message_ids.filtered(
            lambda m: "return label has been downloaded" in (m.body or "").lower()
        )[:1]
        self.assertTrue(message.body)

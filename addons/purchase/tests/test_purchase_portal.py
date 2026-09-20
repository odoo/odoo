from datetime import date, timedelta

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged("post_install", "-at_install")
class TestPurchasePortalRoutes(HttpCaseWithUserPortal):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_portal
        product = cls.env["product.product"].create(
            {"name": "Portal bolts", "type": "consu", "list_price": 4.0}
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "line_ids": [
                    Command.create({"product_id": product.id, "product_qty": 5})
                ],
            }
        )
        cls.token = cls.order._portal_get_or_create_token()
        cls.line = cls.order.line_ids[:1]

    @staticmethod
    def _arrival(days_ahead):
        # the route refuses a date before today, so a literal written on the
        # day the test was written is refused the day after
        return date.today() + timedelta(days=days_ahead)

    def test_order_page_without_token_redirects_home(self):
        res = self.url_open(f"/my/purchase/{self.order.id}")
        self.assertNotIn(f"/my/purchase/{self.order.id}", res.url)
        self.assertNotIn(self.order.name, res.text)

    def test_order_page_with_token_renders(self):
        res = self.url_open(f"/my/purchase/{self.order.id}?access_token={self.token}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.order.name, res.text)

    def test_acknowledge_flags_order_and_redirects(self):
        self.assertFalse(self.order.acknowledged)
        res = self.url_open(
            f"/my/purchase/{self.order.id}?access_token={self.token}&acknowledge=1"
        )
        self.assertIn("message=ack_ok", res.url)
        self.assertTrue(self.order.acknowledged)

    def test_update_line_date_from_portal(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "access_token": self.token,
                str(self.line.id): self._arrival(5).isoformat(),
            },
        }
        res = self.opener.post(
            self.base_url() + f"/my/purchase/{self.order.id}/update",
            json=payload,
        )
        self.assertEqual(res.status_code, 200)
        self.env.invalidate_all()
        self.assertEqual(self.line.date_commitment.date(), self._arrival(5))

    def test_update_line_ignores_invalid_date(self):
        before = self.line.date_commitment
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "access_token": self.token,
                str(self.line.id): "not-a-date",
            },
        }
        self.opener.post(
            self.base_url() + f"/my/purchase/{self.order.id}/update",
            json=payload,
        )
        self.env.invalidate_all()
        self.assertEqual(self.line.date_commitment, before)

    def test_download_edi_serves_xml(self):
        res = self.url_open(
            f"/my/purchase/{self.order.id}/download_edi?access_token={self.token}"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "text/xml")
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))

    def test_vendor_portal_lists_render(self):
        self.authenticate("portal", "portal")
        res_rfq = self.url_open("/my/rfq")
        self.assertEqual(res_rfq.status_code, 200)
        res_orders = self.url_open("/my/purchase")
        self.assertEqual(res_orders.status_code, 200)

    def test_update_returns_json_not_an_http_artifact(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "access_token": self.token,
                str(self.line.id): self._arrival(6).isoformat(),
            },
        }
        res = self.opener.post(
            self.base_url() + f"/my/purchase/{self.order.id}/update",
            json=payload,
        )
        self.assertEqual(res.json()["result"], {"success": True})

    def test_update_reports_failure_for_a_bad_token(self):
        before = self.line.date_commitment
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "access_token": "not-the-token",
                str(self.line.id): self._arrival(7).isoformat(),
            },
        }
        res = self.opener.post(
            self.base_url() + f"/my/purchase/{self.order.id}/update",
            json=payload,
        )
        result = res.json()["result"]
        self.assertFalse(result["success"])
        self.assertTrue(result["error"])
        self.env.invalidate_all()
        self.assertEqual(self.line.date_commitment, before)

    def test_update_rejects_a_token_passed_in_the_query_string(self):
        before = self.line.date_commitment
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {str(self.line.id): self._arrival(8).isoformat()},
        }
        res = self.opener.post(
            self.base_url()
            + f"/my/purchase/{self.order.id}/update?access_token={self.token}",
            json=payload,
        )
        self.assertFalse(res.json()["result"]["success"])
        self.env.invalidate_all()
        self.assertEqual(self.line.date_commitment, before)

    def test_update_page_renders_when_a_line_has_no_expected_arrival(self):
        self.line.write({"date_commitment": False})
        res = self.url_open(
            f"/my/purchase/{self.order.id}?access_token={self.token}&update=True"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("o-purchase-datetimepicker", res.text)

import socket
from unittest.mock import patch

import requests

import odoo.tests
from odoo.libs.guarded_http import GuardedAdapter
from odoo.tests.common import HttpCase, new_test_user
from odoo.tests.transaction_case import _super_send
from odoo.tools.json import scriptsafe as json_safe


@odoo.tests.tagged("-at_install", "post_install")
class TestAttachmentAddUrlHardening(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, login="portal_probe", groups="base.group_portal")
        cls.headers = {"Content-Type": "application/json"}

    def _add_url(self, url):
        return self.url_open(
            "/html_editor/attachment/add_url",
            headers=self.headers,
            data=json_safe.dumps({"params": {"url": url, "res_model": "ir.ui.view"}}),
        ).json()

    def _resolving_publicly(self):
        real_getaddrinfo = socket.getaddrinfo

        def getaddrinfo(host, port, *args, **kwargs):
            if host != "example.com":
                return real_getaddrinfo(host, port, *args, **kwargs)
            return [(2, 1, 6, "", ("93.184.216.34", port))]

        return patch("socket.getaddrinfo", side_effect=getaddrinfo)

    def test_internal_url_is_refused_without_any_request(self):
        self.authenticate("admin", "admin")
        with patch.object(GuardedAdapter, "_send_pinned") as send:
            response = self._add_url("http://127.0.0.1:9/internal")
        send.assert_not_called()
        self.assertIn("error", response)

    def test_link_local_metadata_address_is_refused(self):
        self.authenticate("admin", "admin")
        with patch.object(GuardedAdapter, "_send_pinned") as send:
            response = self._add_url("http://169.254.169.254/latest/meta-data/")
        send.assert_not_called()
        self.assertIn("error", response)

    def test_non_http_schemes_are_refused(self):
        self.authenticate("admin", "admin")
        for url in ("file:///etc/passwd", "gopher://127.0.0.1:70/x", "not-a-url"):
            with patch.object(GuardedAdapter, "_send_pinned") as send:
                response = self._add_url(url)
            send.assert_not_called()
            self.assertIn("error", response, url)

    def test_portal_user_cannot_distinguish_open_from_closed_ports(self):
        self.authenticate("portal_probe", "portal_probe")
        messages = set()
        for url in ("http://127.0.0.1:9991/x", "http://127.0.0.1:9992/x"):
            response = self._add_url(url)
            messages.add(response.get("error", {}).get("data", {}).get("message"))
        self.assertEqual(
            len(messages), 1, "internal targets are distinguishable: %s" % messages
        )

    def test_public_url_still_reaches_the_head_request(self):
        self.authenticate("admin", "admin")
        sent = []

        def send(adapter, request, addresses, options):
            sent.append((request.method, str(addresses[0])))
            response = requests.Response()
            response.status_code = 200
            response.headers["content-type"] = "image/png"
            response.request = request
            response.url = request.url
            response._content = b""
            return response

        with (
            self._resolving_publicly(),
            patch.object(requests.Session, "send", _super_send),
            patch.object(
                GuardedAdapter, "_send_pinned", autospec=True, side_effect=send
            ),
        ):
            response = self._add_url("https://example.com/image.png")
        self.assertEqual(sent, [("HEAD", "93.184.216.34")])
        self.assertNotIn("error", response)
        self.assertEqual(response["result"]["mimetype"], "image/png")

    def test_upstream_request_failure_does_not_escape(self):
        self.authenticate("admin", "admin")
        with (
            self._resolving_publicly(),
            patch.object(requests.Session, "send", _super_send),
            patch.object(
                GuardedAdapter,
                "_send_pinned",
                side_effect=requests.ConnectionError("boom"),
            ),
        ):
            response = self._add_url("https://example.com/unreachable-media")
        self.assertNotIn("error", response)
        self.assertTrue(response["result"]["id"])


@odoo.tests.tagged("-at_install", "post_install")
class TestShapeIllustrationNoTraceback(HttpCase):
    def test_public_binary_attachment_without_url_is_not_a_500(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "photo.png",
                "type": "binary",
                "public": True,
                "res_model": "ir.ui.view",
                "res_id": 0,
                "mimetype": "image/png",
                "raw": b"\x89PNG\r\n\x1a\n" + b"0" * 32,
            }
        )
        self.env.flush_all()
        response = self.url_open("/html_editor/shape/illustration/%s" % attachment.id)
        self.assertEqual(response.status_code, 404)

    def test_unknown_id_is_not_a_500(self):
        response = self.url_open("/html_editor/shape/illustration/999999999")
        self.assertEqual(response.status_code, 404)


@odoo.tests.tagged("-at_install", "post_install")
class TestBusBroadcastFieldValidation(HttpCase):
    def test_unknown_field_is_rejected(self):
        self.authenticate("admin", "admin")
        partner = self.env["res.partner"].create({"name": "broadcast probe"})
        self.env.flush_all()

        def broadcast(field_name):
            return self.url_open(
                "/html_editor/bus_broadcast",
                headers={"Content-Type": "application/json"},
                data=json_safe.dumps(
                    {
                        "params": {
                            "model_name": "res.partner",
                            "field_name": field_name,
                            "res_id": partner.id,
                            "bus_data": {},
                        }
                    }
                ),
            ).json()

        self.assertIn("error", broadcast("no_such_field_here"))
        self.assertNotIn("error", broadcast("comment"))

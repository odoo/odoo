# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.exceptions import ValidationError
from odoo.tests import JsonRpcException, common

from odoo.addons.base.tests.common import HttpCaseWithUserDemo

IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
IMAGE_BYTES = base64.b64decode(IMAGE_BASE64)


class TestUnsplash(common.TransactionCase):
    def test_constraint(self):
        self.env["ir.attachment"].create(
            {
                "name": "attachment",
                "url": "/unsplash/xyz",
                "raw": IMAGE_BASE64,
            },
        )

        with self.assertRaises(ValidationError):
            self.env["ir.attachment"].create(
                {
                    "name": "attachment",
                    "url": "/unsplash/xyz",
                    "raw": "dGVzdA==",
                },
            )


class TestUnsplashHttp(HttpCaseWithUserDemo):
    def test_access(self):
        url_image = "https://images.unsplash.com/foo"
        url_download = "https://api.unsplash.com/photos/foo"
        self.authenticate("demo", "demo")
        with (
            common.MockHTTPClient(url=url_image, return_body=IMAGE_BYTES),
            common.MockHTTPClient(url=url_download),
        ):
            # Upload an unplash image on my partner -> Allowed
            result = self.make_jsonrpc_request(
                "/web_unsplash/attachment/add",
                {
                    "res_model": "res.partner",
                    "res_id": self.partner_demo.id,
                    "query": "foo",
                    "unsplashurls": {
                        "foo": {
                            "url": url_image,
                            "download_url": url_download,
                        },
                    },
                },
            )
            attachment = result[0]
            self.assertEqual(attachment["type"], "binary")
            self.assertEqual(attachment["mimetype"], "image/png")
            self.assertEqual(attachment["res_model"], "res.partner")
            self.assertEqual(attachment["res_id"], self.partner_demo.id)
            self.assertEqual(self.url_open(attachment["url"]).content, IMAGE_BYTES)

            # Upload an unplash image on my user -> Allowed
            result = self.make_jsonrpc_request(
                "/web_unsplash/attachment/add",
                {
                    "res_model": "res.users",
                    "res_id": self.user_demo.id,
                    "query": "foo",
                    "unsplashurls": {
                        "foo": {
                            "url": url_image,
                            "download_url": url_download,
                        },
                    },
                },
            )
            attachment = result[0]
            self.assertEqual(attachment["type"], "binary")
            self.assertEqual(attachment["mimetype"], "image/png")
            self.assertEqual(attachment["res_model"], "res.users")
            self.assertEqual(attachment["res_id"], self.user_demo.id)
            self.assertEqual(self.url_open(attachment["url"]).content, IMAGE_BYTES)

            # Upload an unplash image on another user -> Forbidden
            with self.assertLogs("odoo.http", level="WARNING") as log_catcher, \
                 self.assertRaisesRegex(JsonRpcException, "odoo.exceptions.AccessError"):
                self.make_jsonrpc_request(
                    "/web_unsplash/attachment/add",
                    {
                        "res_model": "res.users",
                        "res_id": self.user_admin.id,
                        "query": "foo",
                        "unsplashurls": {
                            "foo": {
                                "url": url_image,
                                "download_url": url_download,
                            },
                        },
                    },
                )

            self.assertEqual(
                log_catcher.output[0],
                "WARNING:odoo.http:Sorry, you are not allowed to access this document.",
            )

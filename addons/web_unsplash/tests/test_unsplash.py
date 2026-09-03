# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

import requests

from odoo.tests import JsonRpcException, patch

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, Mock

IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
IMAGE_BYTES = base64.b64decode(IMAGE_BASE64)


class TestUnsplashHttp(HttpCaseWithUserDemo):

    def _mocked_save_unsplash_url(self, url, *args, **kwargs):
        """Mock the external requests to Unsplash"""
        response = Mock()
        response.status_code = 200
        if url.startswith("https://images.unsplash.com/"):
            response.content = IMAGE_BYTES
        return response

    def test_access(self):
        url_image = "https://images.unsplash.com/foo"
        url_download = "https://api.unsplash.com/photos/foo"
        self.authenticate("demo", "demo")
        with patch.object(requests, 'get', self._mocked_save_unsplash_url):
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

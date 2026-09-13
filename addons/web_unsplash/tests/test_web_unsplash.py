import base64
from unittest.mock import Mock, patch

from lxml import etree

from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged
from odoo.tools.json import scriptsafe as json_safe


@tagged("post_install", "-at_install")
class TestWebUnsplash(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attachment_model = cls.env["ir.attachment"]
        cls.qweb_image = cls.env["ir.qweb.field.image"]

    def test_erp_manager_can_manage_unsplash(self):
        manager = new_test_user(
            self.env, login="unsplash_mgr", groups="base.group_erp_manager"
        )
        self.assertTrue(manager._can_manage_unsplash_settings())

    def test_basic_user_cannot_manage_unsplash(self):
        user = new_test_user(self.env, login="unsplash_basic", groups="base.group_user")
        self.assertFalse(user._can_manage_unsplash_settings())

    def test_bypass_rights_for_unsplash_binary_url(self):
        self.assertTrue(
            self.attachment_model._can_bypass_rights_on_media_dialog(
                url="/unsplash/photo-1", type="binary"
            )
        )

    def test_no_bypass_for_non_unsplash_url(self):
        self.assertFalse(
            self.attachment_model._can_bypass_rights_on_media_dialog(
                url="/web/image/1", type="binary"
            )
        )

    def test_no_bypass_without_url(self):
        self.assertFalse(
            self.attachment_model._can_bypass_rights_on_media_dialog(type="binary")
        )

    def test_from_html_without_img_returns_false(self):
        element = etree.fromstring("<div>no image here</div>")
        self.assertFalse(
            self.qweb_image.from_html(self.env["res.partner"], None, element)
        )

    def test_from_html_returns_unsplash_attachment_data(self):
        partner = self.env["res.partner"].create({"name": "Author"})
        payload = base64.b64encode(b"unsplash-bytes")
        self.env["ir.attachment"].create(
            {
                "name": "unsplash.jpg",
                "res_model": "res.partner",
                "res_id": partner.id,
                "public": True,
                "url": "/unsplash/photo-1",
                "datas": payload,
            }
        )
        element = etree.fromstring(
            f'<span data-oe-id="{partner.id}"><img src="/unsplash/photo-1"/></span>'
        )
        result = self.qweb_image.from_html(partner, None, element)
        self.assertEqual(result, payload)


GIF_PIXEL = base64.b64decode("R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs=")


@tagged("post_install", "-at_install")
class TestWebUnsplashController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = new_test_user(
            cls.env, login="unsplash_http_admin", groups="base.group_system"
        )

    def _post_unsplash_urls(self, unsplashurls, query="cat"):
        self.authenticate(self.admin_user.login, self.admin_user.login)
        response = self.url_open(
            "/web_unsplash/attachment/add",
            headers={"Content-Type": "application/json"},
            data=json_safe.dumps(
                {"params": {"unsplashurls": unsplashurls, "query": query}}
            ),
        )
        self.assertEqual(200, response.status_code)
        result = response.json()
        self.assertNotIn("error", result, result.get("error"))
        return result["result"]

    def test_single_image_gets_one_extension(self):
        with patch.object(
            GuardedSession,
            "request",
            return_value=Mock(status_code=200, content=GIF_PIXEL),
        ):
            uploads = self._post_unsplash_urls(
                {
                    "key1": {
                        "url": "https://images.unsplash.com/photo-1",
                        "download_url": "https://api.unsplash.com/photos/1/download",
                    }
                }
            )
        self.assertEqual(1, len(uploads))
        self.assertEqual(1, uploads[0]["name"].count(".gif"))
        self.assertTrue(uploads[0]["name"].endswith(".gif"))

    def test_multi_image_batch_does_not_accumulate_extensions(self):
        with patch.object(
            GuardedSession,
            "request",
            return_value=Mock(status_code=200, content=GIF_PIXEL),
        ):
            uploads = self._post_unsplash_urls(
                {
                    "key1": {
                        "url": "https://images.unsplash.com/photo-1",
                        "download_url": "https://api.unsplash.com/photos/1/download",
                    },
                    "key2": {
                        "url": "https://images.unsplash.com/photo-2",
                        "download_url": "https://api.unsplash.com/photos/2/download",
                    },
                    "key3": {
                        "url": "https://images.unsplash.com/photo-3",
                        "download_url": "https://api.unsplash.com/photos/3/download",
                    },
                }
            )
        self.assertEqual(3, len(uploads))
        for upload in uploads:
            self.assertEqual(
                1,
                upload["name"].count(".gif"),
                f"extension accumulated in {upload['name']!r}",
            )

    def test_batch_survives_one_failed_image(self):
        calls = []

        def _image_process_side_effect(image, verify_resolution=True):
            calls.append(image)
            if len(calls) == 2:
                raise UserError("boom")
            return image

        with (
            patch.object(
                GuardedSession,
                "request",
                return_value=Mock(status_code=200, content=GIF_PIXEL),
            ),
            patch(
                "odoo.addons.web_unsplash.controllers.main.image_process",
                side_effect=_image_process_side_effect,
            ),
        ):
            uploads = self._post_unsplash_urls(
                {
                    "key1": {
                        "url": "https://images.unsplash.com/photo-1",
                        "download_url": "https://api.unsplash.com/photos/1/download",
                    },
                    "key2": {
                        "url": "https://images.unsplash.com/photo-2",
                        "download_url": "https://api.unsplash.com/photos/2/download",
                    },
                    "key3": {
                        "url": "https://images.unsplash.com/photo-3",
                        "download_url": "https://api.unsplash.com/photos/3/download",
                    },
                }
            )
        self.assertEqual(3, len(calls))
        self.assertEqual(2, len(uploads))

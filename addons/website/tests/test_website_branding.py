# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

import lxml.html

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user
from odoo.tools import BinaryBytes

from odoo.addons.base.tests.common import BaseCommon

GIF_16PX = base64.b64decode(
    b"R0lGODdhEAAQAIEAAAAAAAAAAAAAAAAAACwAAAAAEAAQAEAIHQABCBxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFgQEBADs=",
)


class TestWebsiteBranding(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].create({"name": "Test Website"})

        cls.designer_user = new_test_user(
            cls.env,
            login="designer_test",
            groups="website.group_website_designer",
        )

        cls.restricted_editor = new_test_user(
            cls.env,
            login="restricted_editor_test",
            groups="website.group_website_restricted_editor",
        )

        cls.valid_image = cls.env["ir.attachment"].create(
            {
                "name": "logo.gif",
                "raw": GIF_16PX,
                "mimetype": "image/gif",
                "public": True,
            },
        )

    def test_branding_saves_each_field_and_refuses_bad_values(self):
        website = self.website.with_user(self.designer_user)

        result = website.update_branding({"name": "  Clean Name  "})
        self.assertEqual(website.name, "Clean Name")
        self.assertEqual(result, {})
        for empty_name in ("   ", ""):
            with self.subTest(name=empty_name):
                result = website.update_branding({"name": empty_name})
                self.assertIn("name", result)
                self.assertEqual(website.name, "Clean Name", "Rejected names should not be written")
        with self.assertRaises(ValidationError):
            website.update_branding("name")

        website.update_branding({"logo": self.valid_image.id})
        self.assertEqual(website.logo.content, GIF_16PX, "The logo should be the attachment data")
        result = website.update_branding({"logo": False})
        self.assertIn("logo", result)
        favicon_before = website.favicon
        result = website.update_branding({"favicon": self.valid_image.id})
        self.assertEqual(result, {})
        self.assertNotEqual(website.favicon, favicon_before, "The favicon should be the attachment, processed")
        website.update_branding({"favicon": False})
        self.assertFalse(website.favicon)

        document = self.env["ir.attachment"].create(
            {
                "name": "document.pdf",
                "raw": b"pdf_data",
                "mimetype": "application/pdf",
                "public": True,
            },
        )
        empty_image = self.env["ir.attachment"].create(
            {"name": "empty.png", "raw": b"", "mimetype": "image/png", "public": True},
        )
        for bad_ref in (document.id, 999999, None, True, 0, "42", empty_image.id):
            with self.subTest(ref=bad_ref):
                result = website.update_branding({"logo": bad_ref})
                self.assertEqual(result, {"logo": "Invalid branding values."})
                self.assertEqual(website.logo.content, GIF_16PX)

        url_image = self.env["ir.attachment"].create(
            {
                "name": "remote",
                "type": "url",
                "url": "https://example.com/remote",
                "mimetype": "application/octet-stream",
                "public": True,
            },
        )
        image_field = self.registry["ir.qweb.field.image"]
        self.patch(image_field, "load_remote_url", lambda self, url: None)
        result = website.update_branding({"logo": url_image.id})
        self.assertEqual(result, {"logo": "The image could not be downloaded from its URL."})
        self.patch(image_field, "load_remote_url", lambda self, url: BinaryBytes(b"downloaded"))
        website.update_branding({"logo": url_image.id})
        self.assertEqual(website.logo.content, b"downloaded")

    def test_branding_refused_field_is_rolled_back(self):
        """A field refused after it was written, for example by an override of
        write, is rolled back."""
        logo_before = self.website.logo.content
        website_write = self.registry["website"].write

        def write_then_fail(records, vals):
            result = website_write(records, vals)
            if "logo" in vals:
                raise UserError("Refused after the write")
            return result

        self.patch(self.registry["website"], "write", write_then_fail)
        website = self.website.with_user(self.designer_user)
        result = website.update_branding({"name": "Kept Name", "logo": self.valid_image.id})

        self.assertEqual(result, {"logo": "Refused after the write"})
        self.env.invalidate_all()
        self.assertEqual(self.website.logo.content, logo_before, "The refused logo should be rolled back")
        self.assertEqual(self.website.name, "Kept Name")

    def test_branding_restricted_editor_and_private_attachment_are_refused(self):
        with self.assertRaises(AccessError):
            self.website.with_user(self.restricted_editor).update_branding({"name": "Hacked Name"})

        private_image = self.env["ir.attachment"].create(
            {
                "name": "private.gif",
                "raw": GIF_16PX,
                "mimetype": "image/gif",
                "public": False,
            },
        )
        website = self.website.with_user(self.designer_user)
        logo_before = self.website.logo.content
        private_result = website.update_branding({"logo": private_image.id})
        missing_result = website.update_branding({"logo": 999999})
        self.assertEqual(private_result["logo"], missing_result["logo"])
        self.assertEqual(self.website.logo.content, logo_before, "The logo should not change")


@tagged("post_install", "-at_install")
class TestWebsiteBrandingRender(HttpCase):
    def test_branding_element_is_not_branded(self):
        self.env["website"].search([], limit=1).name = "Branding Test"
        self.authenticate("admin", "admin")
        html = self.url_open("/?enable_editor=1").text
        branding_el = lxml.html.fromstring(html).get_element_by_id("o_website_branding")
        # Branded, the page save would write it into a view.
        self.assertFalse(branding_el.get("data-oe-model"))
        self.assertEqual(branding_el.get("data-saved-name"), "Branding Test")

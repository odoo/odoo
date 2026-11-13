# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml.html

from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.base.tests.common import BaseCommon

IMAGE = b"image"


class TestWebsiteBranding(BaseCommon):
    _test_user_groups = ("website.group_website_designer",)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].create({"name": "Test Website"})
        cls.valid_image = cls.env["ir.attachment"].create({"name": "logo.gif", "raw": IMAGE, "public": True})
        cls.private_image = cls.env["ir.attachment"].create({"name": "private.gif", "raw": IMAGE})

    def test_branding_saves_each_field_and_refuses_bad_values(self):
        website = self.website
        with self.assertRaises(AccessError):
            website.with_user(self.env.ref("base.public_user")).update_branding({"name": "Hacked Name"})

        self.assertEqual(website.update_branding({"name": "  Clean Name  "}), {})
        self.assertEqual(website.name, "Clean Name")
        for bad_name in ("   ", None):
            self.assertEqual(website.update_branding({"name": bad_name}), {"name": "Invalid branding values."})
        self.assertEqual(website.name, "Clean Name")

        website.update_branding({"logo": self.valid_image.id})
        self.assertEqual(website.logo.content, IMAGE)
        website.update_branding({"favicon": False})
        self.assertFalse(website.favicon)

        Attachment = self.env["ir.attachment"]
        document = Attachment.create({"name": "document.pdf", "raw": b"pdf_data"})
        empty_image = Attachment.create({"name": "empty.png", "raw": b""})
        for bad_ref in (document.id, empty_image.id, self.private_image.id, 999999, "42", True, False):
            with self.subTest(ref=bad_ref):
                self.assertEqual(website.update_branding({"logo": bad_ref}), {"logo": "Invalid branding values."})
                self.assertEqual(website.logo.content, IMAGE)

        url_image = Attachment.create({"name": "remote", "type": "url", "url": "https://example.com/remote"})
        image_field = self.registry["ir.qweb.field.image"]
        self.patch(image_field, "load_remote_url", lambda self, url: None)
        self.assertEqual(
            website.update_branding({"logo": url_image.id}),
            {"logo": "The image could not be downloaded from its URL."},
        )
        self.patch(image_field, "load_remote_url", lambda self, url: BinaryBytes(b"downloaded"))
        self.assertEqual(website.update_branding({"logo": url_image.id}), {})
        self.assertEqual(website.logo.content, b"downloaded")

    def test_branding_refused_field_is_rolled_back(self):
        """A field refused after its write (e.g. by a write override) is rolled back alone."""
        logo_before = self.website.logo.content
        website_write = self.registry["website"].write

        def write_then_fail(records, vals):
            result = website_write(records, vals)
            if "logo" in vals:
                raise UserError("Refused after the write")
            return result

        self.patch(self.registry["website"], "write", write_then_fail)
        result = self.website.update_branding({"name": "Kept Name", "logo": self.valid_image.id})
        self.assertEqual(result, {"logo": "Refused after the write"})
        self.assertEqual(self.website.logo.content, logo_before)
        self.assertEqual(self.website.name, "Kept Name")


@tagged("post_install", "-at_install")
class TestWebsiteBrandingRender(HttpCase):
    def test_branding_element_is_not_saved_into_a_view(self):
        self.authenticate("admin", "admin")
        branding_el = lxml.html.fromstring(self.url_open("/").text).get_element_by_id("o_website_branding")
        # With `data-oe-model`, the page save would write the element into a view.
        self.assertFalse(branding_el.get("data-oe-model"))
        self.assertEqual(branding_el.get("data-saved-name"), self.env["website"].search([], limit=1).name)

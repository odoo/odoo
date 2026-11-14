# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon

MINIMAL_GIF = base64.b64decode(
    b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
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
                "raw": MINIMAL_GIF,
                "mimetype": "image/gif",
                "public": True,
            },
        )

    def test_branding_saves_each_field_and_refuses_bad_values(self):
        website = self.website.with_user(self.designer_user)

        result = website.update_branding({"name": "  Clean Name  "})
        self.assertEqual(website.name, "Clean Name")
        # Every website gets a default favicon on create.
        self.assertEqual(result, {"name": "Clean Name", "has_favicon": True, "errors": {}})
        for empty_name in ("   ", ""):
            with self.subTest(name=empty_name):
                result = website.update_branding({"name": empty_name})
                self.assertIn("name", result["errors"])
                self.assertEqual(website.name, "Clean Name", "Rejected names should not be written")
        with self.assertRaises(ValidationError):
            website.update_branding("name")

        website.update_branding({"logo": self.valid_image.id})
        self.assertEqual(website.logo.content, MINIMAL_GIF, "The logo should be the attachment data")
        result = website.update_branding({"logo": False})
        self.assertIn("logo", result["errors"])
        website.update_branding({"favicon": self.valid_image.id})
        result = website.update_branding({"favicon": False})
        self.assertFalse(result["has_favicon"])
        self.assertFalse(website.favicon)

        # The logo, not the favicon: the favicon processing would refuse a
        # non-image file anyway.
        document = self.env["ir.attachment"].create(
            {
                "name": "document.pdf",
                "raw": b"pdf_data",
                "mimetype": "application/pdf",
                "public": True,
            },
        )
        url_image = self.env["ir.attachment"].create(
            {
                "name": "remote.png",
                "type": "url",
                "url": "https://example.com/remote.png",
                "mimetype": "image/png",
                "public": True,
            },
        )
        empty_image = self.env["ir.attachment"].create(
            {"name": "empty.png", "raw": b"", "mimetype": "image/png", "public": True},
        )
        invalid_reference = "Invalid image reference."
        for bad_ref, error in (
            (document.id, "The selected file must be an image."),
            (999999, "The selected image does not exist or you cannot access it."),
            (None, invalid_reference),
            (True, invalid_reference),
            (0, invalid_reference),
            ("42", invalid_reference),
            (
                url_image.id,
                "This image could not be downloaded from its URL. Please upload the file instead.",
            ),
            (empty_image.id, "The selected image is empty."),
        ):
            with self.subTest(ref=bad_ref):
                result = website.update_branding({"logo": bad_ref})
                self.assertEqual(result["errors"], {"logo": error})
                self.assertEqual(website.logo.content, MINIMAL_GIF)

        # The favicon's data isn't a real image, so its processing on write
        # refuses it.
        not_an_image = self.env["ir.attachment"].create(
            {"name": "fake.png", "raw": b"not an image", "mimetype": "image/png", "public": True},
        )
        result = website.update_branding({"name": "Saved Name", "favicon": not_an_image.id})
        self.assertEqual(list(result["errors"]), ["favicon"])
        self.assertEqual(website.name, "Saved Name")

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

        self.assertEqual(result["errors"], {"logo": "Refused after the write"})
        self.env.invalidate_all()
        self.assertEqual(self.website.logo.content, logo_before, "The refused logo should be rolled back")
        self.assertEqual(self.website.name, "Kept Name")

    def test_branding_restricted_editor_and_private_attachment_are_refused(self):
        with self.assertRaises(AccessError):
            self.website.with_user(self.restricted_editor).update_branding({"name": "Hacked Name"})

        private_image = self.env["ir.attachment"].create(
            {
                "name": "private.gif",
                "raw": MINIMAL_GIF,
                "mimetype": "image/gif",
                "public": False,
            },
        )
        website = self.website.with_user(self.designer_user)
        logo_before = self.website.logo.content
        private_result = website.update_branding({"logo": private_image.id})
        missing_result = website.update_branding({"logo": 999999})
        self.assertEqual(private_result["errors"]["logo"], missing_result["errors"]["logo"])
        self.assertEqual(self.website.logo.content, logo_before, "The logo should not change")

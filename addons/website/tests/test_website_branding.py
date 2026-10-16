import base64

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user

MINIMAL_GIF = base64.b64decode(
    b"R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
)


class TestWebsiteBranding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})

        cls.website = cls.env["website"].create(
            {
                "name": "Test Website",
                "company_id": cls.company_a.id,
            },
        )

        cls.designer_user = new_test_user(
            cls.env,
            login="designer_test",
            groups="website.group_website_designer",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )

        cls.normal_user = new_test_user(
            cls.env,
            login="standard_test",
            groups="base.group_user",
        )

        cls.valid_image = cls.env["ir.attachment"].create(
            {
                "name": "logo.png",
                "raw": MINIMAL_GIF,
                "mimetype": "image/png",
                "company_id": cls.company_a.id,
                "public": True,
            },
        )

    def test_branding_name_validation(self):
        website = self.website.with_user(self.designer_user)

        result = website.update_branding({"name": "  Clean Name  "})
        self.assertEqual(website.name, "Clean Name")
        self.assertEqual(result["name"], "Clean Name")

        with self.assertRaises(ValidationError):
            website.update_branding({"name": "   "})

        with self.assertRaises(ValidationError):
            website.update_branding({"name": ""})

    def test_branding_media_resolution(self):
        website = self.website.with_user(self.designer_user)

        result = website.update_branding({"logo": self.valid_image.id})
        self.assertTrue(result["has_logo"])
        self.assertTrue(website.logo)

        with self.assertRaises(ValidationError):
            website.update_branding({"logo": False})

        website.update_branding({"favicon": self.valid_image.id})
        result = website.update_branding({"favicon": False})
        self.assertFalse(result["has_favicon"])
        self.assertFalse(website.favicon)

        invalid_doc = self.env["ir.attachment"].create(
            {
                "name": "document.pdf",
                "raw": b"pdf_data",
                "mimetype": "application/pdf",
                "company_id": self.company_a.id,
                "public": True,
            },
        )

        with self.assertRaises(ValidationError):
            website.update_branding({"logo": invalid_doc.id})

        with self.assertRaises(ValidationError):
            website.update_branding({"logo": 999999})

    def test_branding_access_rights(self):
        website = self.website.with_user(self.normal_user)
        with self.assertRaises(AccessError):
            website.update_branding({"name": "Hacked Name"})

from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestWebsitePartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Acme"})
        cls.published = cls.env.ref("website_partner.mt_partner_published")
        cls.unpublished = cls.env.ref("website_partner.mt_partner_unpublished")

    def test_website_url_points_to_partner_slug(self):
        expected = "/partners/%s" % self.env["ir.http"]._slug(self.partner)
        self.assertEqual(self.partner.website_url, expected)
        self.assertTrue(self.partner.website_url.endswith(str(self.partner.id)))

    def test_track_subtype_published(self):
        self.partner.is_published = True
        self.assertEqual(
            self.partner._track_subtype({"is_published": False}), self.published
        )

    def test_track_subtype_unpublished(self):
        self.partner.is_published = False
        self.assertEqual(
            self.partner._track_subtype({"is_published": True}), self.unpublished
        )

    def test_track_subtype_falls_back_without_publish_change(self):
        subtype = self.partner._track_subtype({"name": "Renamed"})
        self.assertNotEqual(subtype, self.published)
        self.assertNotEqual(subtype, self.unpublished)


@tagged("post_install", "-at_install")
class TestWebsitePartnerController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Acme", "website_published": False}
        )
        cls.restricted_editor = new_test_user(
            cls.env,
            login="wp_restricted_editor",
            groups="base.group_user,website.group_website_restricted_editor",
        )

    def test_unpublished_partner_404_for_public_user(self):
        slug = self.env["ir.http"]._slug(self.partner)
        response = self.url_open("/partners/%s" % slug)
        self.assertEqual(response.status_code, 404)

    def test_unpublished_partner_200_for_restricted_editor(self):
        self.authenticate("wp_restricted_editor", "wp_restricted_editor")
        slug = self.env["ir.http"]._slug(self.partner)
        response = self.url_open("/partners/%s" % slug)
        self.assertEqual(response.status_code, 200)

    def test_published_partner_200_for_public_user(self):
        self.partner.website_published = True
        slug = self.env["ir.http"]._slug(self.partner)
        response = self.url_open("/partners/%s" % slug)
        self.assertEqual(response.status_code, 200)

    def test_stale_slug_redirects_to_current_slug(self):
        self.partner.website_published = True
        current_slug = self.env["ir.http"]._slug(self.partner)
        response = self.url_open(
            "/partners/%s" % self.partner.id, allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith(current_slug))

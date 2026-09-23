from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.http_routing.tests.common import MockRequest


@tagged("post_install", "-at_install")
class TestGetCurrentWebsite(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")

    def test_01_get_current_website_id(self):
        Website = self.env["website"]

        website1 = self.website
        website1.domain = False

        website2 = Website.create({"name": "My Website 2"})

        self.assertEqual(Website._get_current_website_id(""), website1.id)

        website1.domain = "my-site-1.fr"
        website2.domain = "https://my2ndsite.com:80"

        self.assertEqual(Website._get_current_website_id("my-site-1.fr"), website1.id)

        self.assertEqual(
            Website._get_current_website_id("my-site-1.fr:8069"), website1.id
        )

        self.assertEqual(
            Website._get_current_website_id("my2ndsite.com:80"), website2.id
        )
        self.assertEqual(
            Website._get_current_website_id("my2ndsite.com:8069"), website2.id
        )
        self.assertEqual(Website._get_current_website_id("my2ndsite.com"), website2.id)

        self.assertEqual(Website._get_current_website_id("test.com"), website1.id)

        self.assertEqual(
            Website._get_current_website_id("www.my2ndsite.com"), website1.id
        )

        self.assertEqual(Website._get_current_website_id("my2ndsite.com"), website2.id)
        self.assertEqual(Website._get_current_website_id("my-site-1.fr"), website1.id)

        website1.domain = "site-1.com"
        website2.domain = "even-better-site-1.com"
        self.assertEqual(Website._get_current_website_id("site-1.com"), website1.id)
        self.assertEqual(
            Website._get_current_website_id("even-better-site-1.com"), website2.id
        )

        website1.domain = "Site-1.com"
        website2.domain = "Even-Better-site-1.com"
        self.assertEqual(Website._get_current_website_id("sitE-1.com"), website1.id)
        self.assertEqual(
            Website._get_current_website_id("even-beTTer-site-1.com"), website2.id
        )

        website1.domain = "site-1.com:80"
        website2.domain = "site-1.com:81"
        self.assertEqual(Website._get_current_website_id("site-1.com:80"), website1.id)
        self.assertEqual(Website._get_current_website_id("site-1.com:81"), website2.id)
        self.assertEqual(Website._get_current_website_id("site-1.com:82"), website1.id)
        self.assertEqual(Website._get_current_website_id("site-1.com"), website1.id)

        website2.domain = "düsseldorf.com"
        self.assertEqual(
            Website._get_current_website_id("xn--dsseldorf-q9a.com"), website2.id
        )
        self.assertEqual(Website._get_current_website_id("düsseldorf.com"), website2.id)

        website2.domain = "xn--dsseldorf-q9a.com"
        self.assertEqual(
            Website._get_current_website_id("xn--dsseldorf-q9a.com"), website2.id
        )
        self.assertEqual(Website._get_current_website_id("düsseldorf.com"), website2.id)

    def test_01b_current_website_cache_invalidated_on_create_unlink(self):
        Website = self.env["website"]
        self.website.domain = "primary.example"

        self.assertFalse(
            Website._get_current_website_id("cache-site.example", fallback=False)
        )

        w2 = Website.create({"name": "Cache Site", "domain": "cache-site.example"})
        self.assertEqual(
            Website._get_current_website_id("cache-site.example", fallback=False),
            w2.id,
            "create() must invalidate the stale 'no match' website-id cache.",
        )

        w2.unlink()
        self.assertFalse(
            Website._get_current_website_id("cache-site.example", fallback=False),
            "unlink() must invalidate the stale website-id cache.",
        )

    def test_02_signup_user_website_id(self):
        website = self.website
        website.specific_user_account = True

        user = self.env["res.users"].create(
            {
                "website_id": website.id,
                "login": "sad@mail.com",
                "name": "Hope Fully",
                "group_ids": [
                    Command.link(self.env.ref("base.group_portal").id),
                    Command.unlink(self.env.ref("base.group_user").id),
                ],
            }
        )
        self.assertTrue(user.website_id == user.partner_id.website_id == website)

    @mute_logger("odoo.addons.rpc.controllers.xmlrpc")
    def test_03_rpc_signin_user_website_id(self):
        def rpc_login_user_demo():
            return self.xmlrpc_common.login(self.env.cr.dbname, "demo", "demo")

        website1 = self.website
        website1.domain = self.base_url()

        website2 = self.env["website"].create({"name": "My Website 2"})
        website2.domain = False

        self.user_demo.website_id = website1
        self.assertTrue(rpc_login_user_demo())

        self.user_demo.website_id = website2
        self.assertFalse(rpc_login_user_demo())

    def test_context_website_id_is_checked_once_per_request(self):
        Website = self.env["website"]
        gone = Website.create({"name": "Gone"})
        gone_id = gone.id
        gone.unlink()
        with MockRequest(self.env):
            from_context = Website.with_context(website_id=self.website.id)
            self.assertEqual(from_context.get_current_website(), self.website)
            with self.assertQueryCount(0):
                for _ in range(3):
                    self.assertEqual(from_context.get_current_website(), self.website)
            self.assertEqual(
                Website.with_context(website_id=gone_id).get_current_website(),
                self.website,
                "a stale context website_id must fall through to the domain lookup",
            )

    def test_recursive_current_website(self):
        Website = self.env["website"]
        self.env["ir.access"].create(
            {
                "name": "Recursion Test",
                "model_id": self.env.ref("website.model_website").id,
                "group_id": self.env.ref("base.group_everyone").id,
                "kind": "guard",
                "operation": "crud",
                "domain": repr([(1, "=", 1)]),
            }
        )
        self.env.registry.clear_cache()
        failed = False
        with MockRequest(self.env, website=self.website):
            try:
                Website.with_user(self.env.ref("base.public_user").id).search([])
            except RecursionError:
                failed = True
        if failed:
            self.fail("There should not be a RecursionError")

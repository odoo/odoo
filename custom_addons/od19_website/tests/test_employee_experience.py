import datetime

from odoo import Command
from odoo.addons.od19_website.controllers.main import AutoInfoWebsite
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGreetingHelper(TransactionCase):
    def test_greeting_buckets(self):
        controller = AutoInfoWebsite()
        self.assertEqual(controller._od19_greeting(9), "สวัสดีตอนเช้า")
        self.assertEqual(controller._od19_greeting(13), "สวัสดีตอนบ่าย")
        self.assertEqual(controller._od19_greeting(20), "สวัสดีตอนเย็น")

    def test_initials(self):
        controller = AutoInfoWebsite()
        self.assertEqual(controller._od19_initials("Somchai Jaidee"), "SJ")
        self.assertEqual(controller._od19_initials("Somchai"), "SO")
        self.assertEqual(controller._od19_initials(""), "?")


@tagged("post_install", "-at_install")
class TestPortalHeroHtml(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "Hero Tester",
                "login": "hero_tester",
                "password": "hero_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_portal_hero_uses_time_greeting(self):
        self.authenticate("hero_tester", "hero_tester")
        html = self.url_open("/employee-portal").text
        self.assertTrue(
            "สวัสดีตอนเช้า" in html
            or "สวัสดีตอนบ่าย" in html
            or "สวัสดีตอนเย็น" in html
        )
        self.assertIn('od19-avatar', html)

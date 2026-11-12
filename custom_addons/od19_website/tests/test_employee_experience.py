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


@tagged("post_install", "-at_install")
class TestPortalMyDayHtml(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "My Day Tester",
                "login": "my_day_tester",
                "password": "my_day_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_my_day_strip_present(self):
        self.authenticate("my_day_tester", "my_day_tester")
        html = self.url_open("/employee-portal").text
        self.assertIn('id="od19-my-day"', html)
        self.assertIn('data-od19-me-summary="/employee-portal/me-summary"', html)
        self.assertIn('data-od19-field="attendance"', html)
        self.assertIn('data-od19-field="approvals"', html)

    def test_my_schedule_and_anchor_present(self):
        self.authenticate("my_day_tester", "my_day_tester")
        html = self.url_open("/employee-portal").text
        self.assertIn('id="od19-my-schedule"', html)
        self.assertIn('id="od19-recognition-anchor"', html)

    def test_my_day_js_in_frontend_bundle(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_frontend")[0]
        urls = [asset["url"] for asset in assets]
        self.assertIn("/od19_website/static/src/js/od19_my_day.js", urls)

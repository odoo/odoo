from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestShortcutMenuAsset(HttpCase):
    """The systray shortcut menu must be wired into the backend bundle."""

    def test_shortcut_menu_in_backend_bundle(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        urls = [asset["url"] for asset in assets]
        self.assertIn(
            "od19_website/static/src/js/od19_shortcut_menu.js",
            urls,
        )


@tagged("post_install", "-at_install")
class TestEmployeePortalGuideCard(HttpCase):
    """The Quick Access grid must expose the user-guide shortcut card."""

    def test_quick_access_has_user_guide_card(self):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": "Shortcut Tester",
            "login": "od19_shortcut_tester",
            "email": "od19.shortcut.tester@example.com",
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")

        html = self.url_open("/employee-portal").text

        self.assertIn("คู่มือการใช้งาน", html)
        self.assertIn("/web#action=web_tour.tour_action", html)
        # The guide card joins the nine existing Quick Access cards.
        self.assertGreaterEqual(html.count("od19-portal-card"), 10)

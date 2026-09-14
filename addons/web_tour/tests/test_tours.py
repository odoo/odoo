from markupsafe import Markup

from odoo import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon, HttpCase


@tagged("post_install", "-at_install")
class TestTour(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tour_1 = cls.env["web_tour.tour"].create(
            {
                "name": "my_tour",
                "url": "my_url",
                "sequence": 2,
                "step_ids": [
                    Command.create(
                        {
                            "content": "Click here",
                            "trigger": "button",
                            "run": "click",
                        }
                    ),
                ],
            }
        )

        cls.tour_2 = cls.env["web_tour.tour"].create(
            {
                "name": "your_tour",
                "url": "my_url",
                "custom": True,
                "sequence": 3,
                "step_ids": [
                    Command.create(
                        {
                            "content": "Click here",
                            "trigger": "button",
                            "run": "click",
                        }
                    ),
                    Command.create(
                        {
                            "content": "Edit here",
                            "trigger": "input",
                            "run": "edit 5",
                        }
                    ),
                ],
            }
        )

        cls.tour_3 = cls.env["web_tour.tour"].create(
            {
                "name": "their_tour",
                "url": "my_url",
                "sequence": 1,
            }
        )

    def test_get_tour_json_by_name(self):
        tour = self.env["web_tour.tour"].get_tour_json_by_name("my_tour")

        self.assertEqual(
            tour,
            {
                "name": "my_tour",
                "url": "my_url",
                "custom": False,
                "rainbowManMessage": Markup(
                    "<span><b>Good job!</b> You went through all steps of this tour.</span>"
                ),
                "steps": [
                    {
                        "content": "Click here",
                        "trigger": "button",
                        "tooltipPosition": "bottom",
                        "run": "click",
                    }
                ],
            },
        )

    def test_get_current_tour(self):
        self.env.user.tour_enabled = True
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(tour["name"], "their_tour")
        self.env["web_tour.tour"].consume("their_tour")
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(tour["name"], "my_tour")
        self.env["web_tour.tour"].consume("my_tour")
        self.env.user.tour_enabled = False
        tour = self.env["web_tour.tour"].get_current_tour()
        self.assertEqual(bool(tour), False)


@tagged("post_install", "-at_install")
class WebTourHttp(HttpCase):
    def test_sanity_automatic(self):
        ResUsers = self.env["res.users"]
        IrAsset = self.env["ir.asset"]
        admin = ResUsers.search(ResUsers._get_domain_login("admin"))
        admin.tour_enabled = False

        tour_auto_bundle = IrAsset._get_asset_paths("web_tour.automatic", {})
        self.assertTrue(len(tour_auto_bundle) > 0)

        IrAsset.create(
            [
                {
                    "name": file[0],
                    "path": file[0],
                    "bundle": "web.assets_tests",
                    "directive": "remove",
                }
                for file in tour_auto_bundle
            ]
        )
        self.env.registry.clear_cache("assets")

        ready = "document.readyState === 'complete'"

        code = """
        (() => {
            const errors = [];
            for (const module of ["@odoo/hoot-dom", "@web_tour/js/tour_step"]) {
                if (odoo.loader.modules.get(module)) {
                    errors.push(module)
                }
            }
            if (!errors.length) {
                console.log("test successful");
            } else {
                console.error(`Modules "${errors.join(", ")}" should not be available at this point`)
            }
        })()
        """
        self.browser_js("/odoo?debug=tests", code, ready=ready, login="admin")
        if "website" in IrAsset._get_addons_installed():
            self.browser_js("/?debug=tests", code, ready=ready, login="admin")

    def test_sanity_onboarding(self):
        IrAsset = self.env["ir.asset"]
        ResUsers = self.env["res.users"]
        admin = ResUsers.search(ResUsers._get_domain_login("admin"))
        admin.tour_enabled = False

        self.env["ir.ui.view"].create(
            {
                "name": "test_sanity_onboarding",
                "inherit_id": self.env.ref("web.conditional_assets_tests").id,
                "arch": """
                <xpath expr="/t[@t-name='web.conditional_assets_tests']/t" position="before">
                    <t t-set="test_mode_enabled" t-value="False" />
                </xpath>
            """,
            }
        )

        ready = "document.readyState === 'complete'"

        code = """
        (() => {
            const errors = [];
            for (const module of ["@odoo/hoot-dom", "@web_tour/js/tour_step"]) {
                if (odoo.loader.modules.get(module)) {
                    errors.push(module)
                }
            }
            if (!errors.length) {
                console.log("test successful");
            } else {
                console.error(`Modules "${errors.join(", ")}" should not be available at this point`)
            }
        })()
        """
        self.browser_js("/odoo?debug=0", code, ready=ready, login="admin")
        if "website" in IrAsset._get_addons_installed():
            self.browser_js("/?debug=0", code, ready=ready, login="admin")

from odoo.tests import tagged
from odoo import Command
from odoo.addons.base.tests.common import BaseCommon, HttpCase
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestTour(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tour_1 = cls.env["web_tour.tour"].create({
            "name": "my_tour",
            "url": "my_url",
            "sequence": 2,
            "step_ids": [Command.create(
                {
                    "content": "Click here",
                    "trigger": "button",
                    "run": "click",
                }),
            ]
        })

        cls.tour_2 = cls.env["web_tour.tour"].create({
            "name": "your_tour",
            "url": "my_url",
            "custom": True,
            "sequence": 3,
            "step_ids": [Command.create({
                    "content": "Click here",
                    "trigger": "button",
                    "run": "click",
                }),
                Command.create({
                    "content": "Edit here",
                    "trigger": "input",
                    "run": "edit 5",
                }),
            ]
        })

        cls.tour_3 = cls.env["web_tour.tour"].create({
            "name": "their_tour",
            "url": "my_url",
            "sequence": 1,
        })

    def test_get_tour_json_by_name(self):
        tour = self.env["web_tour.tour"].get_tour_json_by_name("my_tour")

        self.assertEqual(tour, {
            "name": "my_tour",
            "url": "my_url",
            "custom": False,
            "rainbowManMessage": Markup("<span><b>Good job!</b> You went through all steps of this tour.</span>"),
            "steps": [{
                "content": "Click here",
                "trigger": "button",
                "tooltipPosition": "bottom",
                "run": "click",
            }]
        })

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


@tagged('post_install', '-at_install')
class WebTourHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eager_files = ["/web_tour/static/src/js/tour_automatic/tour_helpers.js"]

    def test_sanity_automatic(self):
        ResUsers = self.env["res.users"]
        IrAsset = self.env["ir.asset"]
        admin = ResUsers.search(ResUsers._get_login_domain("admin"))
        # Do not start any onboarding tour on startup
        admin.tour_enabled = False

        tour_auto_bundle = IrAsset._get_asset_paths("web_tour.automatic", {})
        self.assertTrue(len(tour_auto_bundle) > 0)

        # web.assets_tests by default contain all the necessary code to start tours
        # immediately without loading an additional bundle
        # Disable this feature to see errors in tour declaration
        create_vals = []
        for file in tour_auto_bundle:
            if file[0] not in self.eager_files:
                create_vals.append({
                    "name": file[0],
                    "path": file[0],
                    "bundle": "web.assets_tests",
                    "directive": "remove",
                })
        IrAsset.create(create_vals)

        # Wait for page and resources to be loaded
        # This should ensure all tour files have been executed
        ready = "document.readyState === 'complete'"

        # Assert lazy resources are not available
        code = """
        odoo.define("@web_tour/../tests/sanity_test", [], () => {
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
        })
        """
        self.browser_js("/odoo?debug=tests", code, ready=ready, login="admin")
        if "website" in IrAsset._get_installed_addons_list():
            self.browser_js("/?debug=tests", code, ready=ready, login="admin")

    def test_sanity_onboarding(self):
        IrAsset = self.env["ir.asset"]
        ResUsers = self.env["res.users"]
        admin = ResUsers.search(ResUsers._get_login_domain("admin"))
        # Do not start any onboarding tour on startup
        admin.tour_enabled = False

        # We want to boot Odoo as in real life (not loading assets for tests)
        # debug will be equal to 0
        # and the **server** debug mode to False
        self.env["ir.ui.view"].create({
            "name": "test_sanity_onboarding",
            "inherit_id": self.env.ref("web.conditional_assets_tests").id,
            "arch": """
                <xpath expr="/t[@t-name='web.conditional_assets_tests']/t" position="before">
                    <t t-set="test_mode_enabled" t-value="False" />
                </xpath>
            """
        })

        # This should ensure all tour files have been executed
        ready = "document.readyState === 'complete'"

        # Assert lazy resources are not available
        code = """
        odoo.define("@web_tour/../tests/sanity_test", [], () => {
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
        })
        """
        self.browser_js("/odoo?debug=0", code, ready=ready, login="admin")
        if "website" in IrAsset._get_installed_addons_list():
            self.browser_js("/?debug=0", code, ready=ready, login="admin")


@tagged('post_install', '-at_install')
class TestOnboardingToursAuto(HttpCase):

    # Tours covered by this test class. Add tour names here as they are
    # migrated to XML steps and validated to run without any Python setup.
    _tested_tours = {
        'sale_tour',
    }

    def test_onboarding_tours(self):
        """Run the onboarding tours listed in _tested_tours."""
        admin = self.env.ref('base.user_admin')
        admin.email = 'admin@example.com'

        domain = [('custom', '=', False), ('step_ids', '!=', False), ('name', 'in', list(self._tested_tours))]
        tours = self.env['web_tour.tour'].search(domain)
        if not tours:
            self.skipTest("No tested onboarding tours found in database")

        for tour in tours:
            with self.subTest(tour=tour.name):
                _logger.info("Running onboarding tour: %s", tour.name)
                tour.user_consumed_ids = [Command.clear()]
                self.start_tour(tour.url or '/odoo', tour.name, login='admin')

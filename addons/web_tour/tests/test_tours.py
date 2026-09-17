import io

from lxml import etree

from odoo.tests import tagged
from odoo import Command
from odoo.tools.convert import convert_file, convert_xml_import
from odoo.addons.base.tests.common import BaseCommon, HttpCase
from markupsafe import Markup


@tagged('post_install', '-at_install')
class TestTour(BaseCommon):

    _test_user_groups = None  # FIXME list needed groups

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

    def test_export_xml_file(self):
        tour = self.env["web_tour.tour"].create({
            "name": "My Tour (v2)!",
            "url": "/odoo/my_action",
            "sequence": 7,
            "custom": True,
            "active": False,
            "rainbow_man_message": "<p>Well done</p>",
            "step_ids": [
                Command.create({"trigger": "button.first", "run": "click", "content": "First", "tooltip_position": "left", "sequence": 0}),
                Command.create({"trigger": "input.second", "run": "edit 5", "sequence": 1}),
                Command.create({"trigger": "button.third", "sequence": 2}),
            ],
        })
        action = tour.export_xml_file()
        self.assertEqual(action["type"], "ir.actions.act_url")

        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "web_tour.tour"),
            ("res_id", "=", tour.id),
            ("name", "=", "My Tour (v2)!.xml"),
        ])
        self.assertTrue(attachment)
        self.assertIn(str(attachment.id), action["url"])

        root = etree.fromstring(attachment.raw.content)
        self.assertEqual(root.find("./record[@model='web_tour.tour']").get("id"), "My_Tour__v2__")

        def tour_values(tour):
            return {
                "name": tour.name,
                "url": tour.url,
                "sequence": tour.sequence,
                "custom": tour.custom,
                "active": tour.active,
                "rainbow_man_message": tour.rainbow_man_message,
                "steps": [
                    (step.trigger, step.run, step.content, step.tooltip_position)
                    for step in tour.step_ids
                ],
            }

        expected = tour_values(tour)
        xml_file = io.BytesIO(attachment.raw.content)
        xml_file.name = attachment.name
        tour.unlink()

        convert_xml_import(self.env, "web_tour", xml_file)
        self.env.invalidate_all()
        self.assertEqual(tour_values(self.env.ref("web_tour.My_Tour__v2__")), expected)


@tagged('post_install', '-at_install')
class WebTourHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eager_files = ["/web_tour/static/src/tour_helpers/tour_helpers.js"]

    def test_xml_tour(self):
        convert_file(self.env, "web_tour", "tests/test_xml_tour.xml", idref={}, mode="init", noupdate=False)
        tour = self.env.ref("web_tour.test_xml_tour")
        self.start_tour(tour.url, tour.name, login="admin")

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
            for (const module of ["@odoo/hoot-dom", "@web_tour/tour_step"]) {
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
            for (const module of ["@odoo/hoot-dom", "@web_tour/tour_step"]) {
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

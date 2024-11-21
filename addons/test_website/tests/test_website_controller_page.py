from lxml import html

from odoo.tools import mute_logger
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

from odoo.addons.website.controllers.model_page import ModelPageController

@tagged('post_install', '-at_install')
class TestWebsiteControllerPage(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["ir.model"]._get("test.model.exposed")

        cls.model_acl = cls.env["ir.model.access"].create({
            "name": "test acl expose",
            "model_id": cls.model.id,
            "group_id": cls.env.ref("website.website_page_controller_expose").id,
            "perm_read": True,
        })

        cls.listing_view = cls.env["ir.ui.view"].create({
            "type": "qweb",
            "model": cls.model.model,
            "arch": """<t t-call="website.layout">
                <t t-set="_activeClasses" t-translation="off">border-primary</t>
                <div t-attf-class="listing_layout_switcher btn-group ms-3" t-att-data-active-classes="_activeClasses" t-att-data-view-id="view_id">
                    <input type="radio" class="btn-check" name="wstudio_layout" id="o_wstudio_apply_grid" value="grid" t-att-checked="'checked' if layout_mode != 'list' else None"/>
                    <label t-attf-class="btn btn-light #{_activeClasses if layout_mode != 'list' else None} o_wstudio_apply_grid" title="Grid" for="o_wstudio_apply_grid">
                        <i class="fa fa-th-large"/>
                    </label>
                    <input type="radio" class="btn-check" name="wstudio_layout" id="o_wstudio_apply_list" t-att-checked="'checked' if layout_mode == 'list' else None" value="list"/>
                    <label t-attf-class="btn btn-light #{_activeClasses if layout_mode == 'list' else None} o_wstudio_apply_list" title="List" for="o_wstudio_apply_list">
                        <i class="oi oi-view-list"/>
                    </label>
                </div>

                <div t-attf-class="row mx-n2 mt8 #{'o_website_grid' if layout_mode == 'grid' else 'o_website_list'}">
                    <t t-foreach="records" t-as="record">
                        <a class="test_record_listing" t-out="record.display_name" t-att-href="record_to_url(record)" />
                    </t>
                </div>
            </t> """
        })

        cls.single_view = cls.env["ir.ui.view"].create({
            "type": "qweb",
            "model": cls.model.model,
            "arch": """<t t-call="website.layout">
                <div class="test_record" t-out="record.display_name" />
            </t> """
        })

        cls.listing_controller_page = cls.env["website.controller.page"].create({
            "name": "Exposed Model",
            "view_id": cls.listing_view.id,
            "record_view_id": cls.single_view.id,
            "record_domain": "[('name', '=ilike', 'test_partner_%')]",
            "website_published": True,
        })

        partner_data = {}
        if "is_published" in cls.env[cls.model.model]._fields:
            partner_data["is_published"] = True

        records_to_create = [dict(name=f"test_partner_{i}", **partner_data) for i in range(2)]
        cls.exposed_records = cls.env[cls.model.model].create(records_to_create)

    def test_cannot_bypass_read_rights(self):
        self.env["ir.model.access"].search([("model_id", "=", self.model.id)]).perm_read = False

        with self.assertRaises(AccessError) as cm:
            self.env["website.controller.page"].with_user(2).create({
                "name": "Exposed Model",
                "website_id": False,
                "view_id": self.single_view.id,
                "record_domain": "[('name', '=ilike', 'test_partner_%')]",
                "website_published": True,
            })
        self.assertEqual(str(cm.exception).split("\n")[0], "You are not allowed to access 'Website Model Test Exposed' (test.model.exposed) records.")

    def test_access_rights_and_rules(self):
        self.authenticate(None, None)
        self.model_acl.active = False
        with mute_logger("odoo.http"):
            response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}")
        self.assertEqual(response.status_code, 403)

        self.model_acl.active = True
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}")
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.content.decode())
        rec_nodes = tree.xpath("//a[@class='test_record_listing']")
        self.assertEqual(len(rec_nodes), 2)

        self.env["ir.rule"].create({
            "name": "dummy",
            "model_id": self.model.id,
            "domain_force": "[('name', '=', 'test_partner_1')]",
            "groups": self.env.ref("base.group_public"),
        })
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}")
        tree = html.fromstring(response.content.decode())
        rec_nodes = tree.xpath("//a[@class='test_record_listing']")
        self.assertEqual(len(rec_nodes), 1)

    def test_expose_model(self):
        self.authenticate(None, None)

        slug = self.env['ir.http']._slug
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}")
        tree = html.fromstring(response.content.decode())
        rec_nodes = tree.xpath("//a[@class='test_record_listing']")
        self.assertEqual(len(rec_nodes), 2)
        for n, record in zip(rec_nodes, self.exposed_records):
            self.assertEqual(n.get("href"), f"/model/{self.listing_controller_page.name_slugified}/{slug(record)}")

        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}/{slug(self.exposed_records[0])}")
        tree = html.fromstring(response.content.decode())
        self.assertEqual(len(tree.xpath("//div[@class='test_record']")), 1)

        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}/fake-slug-{self.exposed_records[0].id}")
        self.assertEqual(response.status_code, 404)

        non_reachable_record = self.env[self.model.model].create({"name": "non_reachable"})
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}/{slug(non_reachable_record)}")
        self.assertEqual(response.status_code, 404)

        response = self.url_open("/model/some-other-slug")
        self.assertEqual(response.status_code, 404)

        self.listing_controller_page.website_published = False
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}")
        self.assertEqual(response.status_code, 404)

    def test_search_listing(self):
        self.authenticate(None, None)

        slug = self.env['ir.http']._slug
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}?search=1")
        tree = html.fromstring(response.content.decode())
        rec_nodes = tree.xpath("//a[@class='test_record_listing']")
        self.assertEqual(len(rec_nodes), 1)
        self.assertEqual(rec_nodes[0].get("href"), f"/model/{self.listing_controller_page.name_slugified}/{slug(self.exposed_records[1])}")

        self.patch(ModelPageController, "pager_step", 1)
        response = self.url_open(f"/model/{self.listing_controller_page.name_slugified}/page/2")
        tree = html.fromstring(response.content.decode())
        rec_nodes = tree.xpath("//a[@class='test_record_listing']")
        self.assertEqual(len(rec_nodes), 1)
        self.assertEqual(rec_nodes[0].get("href"), f"/model/{self.listing_controller_page.name_slugified}/{slug(self.exposed_records[1])}")

    def test_default_layout(self):
        self.assertEqual(self.listing_controller_page.default_layout, 'grid')
        self.start_tour('/model/exposed-model', 'website_controller_page_listing_layout', login='admin')
        self.assertEqual(self.listing_controller_page.default_layout, 'list')
        #check that the user that has not previously interacted with the layout switcher will prompt on the default layout
        self.start_tour('/model/exposed-model', 'website_controller_page_default_page_check', login='admin')

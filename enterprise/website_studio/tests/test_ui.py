# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
from lxml import etree

import odoo.tests
from odoo import Command

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def create_empty_app(self):

        tag_model_vals = {
            'name': 'Tags',
            'model': 'x_test_tag',
            'field_id': [
                Command.create({
                    'name': 'x_name',
                    'ttype': 'char',
                    'required': True,
                    'field_description': 'Name',
                    'copied': True,
                }),
                Command.create({
                    'name': 'x_color',
                    'ttype': 'integer',
                    'field_description': 'Color',
                    'copied': True,
                }),
            ],
        }
        self.tagModel = self.env['ir.model'].create(tag_model_vals)
        self.tagModel._setup_access_rights()

        tag_field = Command.create({
                'name': 'x_studio_tag_ids',
                'ttype': 'many2many',
                'relation': tag_model_vals['model'],
                'field_description': 'Tags',
                'relation_table': 'x_test_tag_rel',
                'column1': 'x_test_tag_id',
                'column2': 'x_tag_id',
                'copied': True,
        })

        self.newModel = self.env['ir.model'].create({
            'name': 'Test Model',
            'model': 'x_test_model',
            'field_id': [
                (0, 0, {'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
                (0, 0, {'name': 'x_studio_currency_id', 'ttype': 'many2one', 'relation': 'res.currency', 'field_description': 'Currency'}),
                (0, 0, {'name': 'x_studio_monetary', 'ttype': 'monetary', 'field_description': 'Monetary', 'currency_field': 'x_studio_currency_id'}),
                (0, 0, {'name': 'x_studio_html', 'ttype': 'html', 'field_description': 'HTML field'}),
                (0, 0, {'name': 'x_studio_image', 'ttype': 'binary', 'field_description': 'Image'}),
                tag_field,
            ]
        })
        self.newModel._setup_access_rights()

        self.formView = self.env["ir.ui.view"].create({
            "name": "simpleView",
            "model": "x_test_model",
            "type": "form",
            "arch": '''
                <form>
                    <sheet>
                        <field class="oe_avatar" widget="image" name="x_studio_image"/>
                        <group>
                            <field name="x_name" />
                            <field name="x_studio_currency_id"/>
                            <field name="x_studio_monetary"/>
                            <field name="x_studio_html"/>
                            <field name="x_studio_tag_ids" widget="many2many_tags" options="{'color_field': 'x_color'}"/>
                        </group>
                    </sheet>
                </form>
            '''
        })

        self.listView = self.env["ir.ui.view"].create({
            "name": "simpleView",
            "model": "x_test_model",
            "type": "list",
            "arch": '''
                <list>
                    <field name="x_name" />
                    <field name="x_studio_currency_id"/>
                    <field name="x_studio_monetary"/>
                    <field name="x_studio_tag_ids"/>
                </list>
            '''
        })

        self.newAction = self.env["ir.actions.act_window"].create({
            "name": "simple model",
            "res_model": "x_test_model",
            "view_ids": [Command.create({"view_id": self.listView.id, "view_mode": "list"}), Command.create({"view_id": self.formView.id, "view_mode": "form"})],
        })

        self.newActionXmlId = self.env["ir.model.data"].create({
            "name": "studio_app_action",
            "model": "ir.actions.act_window",
            "module": "web_studio",
            "res_id": self.newAction.id,
        })

        self.newMenu = self.env["ir.ui.menu"].create({
            "name": "StudioApp",
            "action": "ir.actions.act_window,%s" % self.newAction.id
        })

        self.newMenuXmlId = self.env["ir.model.data"].create({
            "name": "studio_app_menu",
            "model": "ir.ui.menu",
            "module": "web_studio",
            "res_id": self.newMenu.id,
        })

        self.currency = self.env['res.currency'].create({
            'name': 'Gold',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
        })

    def test_listing_and_page_creation(self):
        image_data = ("/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8Q"
                      "EBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=")

        self.create_empty_app()
        self.env['x_test_model'].create({
            'x_name': 'Record 1',
            'x_studio_currency_id': self.currency.id,
            'x_studio_monetary': 3.53,
            'x_studio_html': '<div id="html_id">HTML value</div>',
            'x_studio_tag_ids': [
                Command.create({'x_name': 'A tag', 'x_color': 1}),
                Command.create({'x_name': 'A second tag', 'x_color': 2}),
                Command.create({'x_name': 'A third tag', 'x_color': 3}),
                Command.create({'x_name': 'Another tag', 'x_color': 4}),
            ],
            'x_studio_image': image_data,
        })

        self.start_tour("/odoo", 'website_studio_listing_and_page', login="admin", timeout=3600)
        created_pages = self.env["website.controller.page"].search([])
        self.assertEqual(len(created_pages), 1)

        listing = created_pages
        self.assertEqual(listing.name_slugified, 'mycustom-name')
        self.assertEqual(len(listing.menu_ids), 1)
        self.assertEqual(len(listing.view_id), 1)
        self.assertTrue(listing.record_view_id.exists())

        listing_tree = etree.fromstring(listing.view_id.arch)
        name_field = listing_tree.xpath("//span[@t-field='record.x_name']")
        self.assertEqual(len(name_field), 1)
        tag_loop = listing_tree.xpath("//t[@t-foreach='record.x_studio_tag_ids']")
        self.assertEqual(len(tag_loop), 1)
        tag_field = listing_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = listing_tree.xpath("//div[@t-field='record.x_studio_image']")
        self.assertEqual(len(image_field), 1)
        self.assertEqual(image_field[0].get("t-options-widget"), "'image'")
        monetary_field = listing_tree.xpath("//span[@t-field='record.x_studio_monetary']")
        self.assertEqual(len(monetary_field), 1)

        page_tree = etree.fromstring(listing.record_view_id.arch)
        name_field = page_tree.xpath("//span[@t-field='record.x_name']")
        self.assertEqual(len(name_field), 2)
        tag_field = page_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = page_tree.xpath("//div[@t-field='record.x_studio_image']")
        self.assertEqual(len(image_field), 1)
        self.assertEqual(image_field[0].get("t-options-widget"), "'image'")
        monetary_field = page_tree.xpath("//span[@t-field='record.x_studio_monetary']")
        self.assertEqual(len(monetary_field), 1)

    def test_listing_without_page_creation(self):
        image_data = ("/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8Q"
                      "EBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=")

        self.env['website'].create({'name': 'Second website to display listings'})
        self.create_empty_app()
        self.env['x_test_model'].create({
            'x_name': 'Record 1',
            'x_studio_currency_id': self.currency.id,
            'x_studio_monetary': 3.53,
            'x_studio_html': '<div id="html_id">HTML value</div>',
            'x_studio_tag_ids': [
                Command.create({'x_name': 'A tag', 'x_color': 1}),
                Command.create({'x_name': 'A second tag', 'x_color': 2}),
                Command.create({'x_name': 'A third tag', 'x_color': 3}),
                Command.create({'x_name': 'Another tag', 'x_color': 4}),
            ],
            'x_studio_image': image_data,
        })

        self.start_tour("/odoo", 'website_studio_listing_without_page', login="admin", watch=False, timeout=3600)
        created_pages = self.env["website.controller.page"].search([])
        self.assertEqual(len(created_pages), 1)
        self.assertEqual(created_pages[0].name_slugified, 'mycustom-name')
        self.assertEqual(len(created_pages[0].menu_ids), 1)
        self.assertEqual(len(created_pages[0].view_id), 1)
        self.assertFalse(created_pages[0].record_view_id)

        listing_tree = etree.fromstring(created_pages[0].view_id.arch)
        name_field = listing_tree.xpath("//span[@t-field='record.x_name']")
        self.assertEqual(len(name_field), 1)
        tag_loop = listing_tree.xpath("//t[@t-foreach='record.x_studio_tag_ids']")
        self.assertEqual(len(tag_loop), 1)
        tag_field = listing_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = listing_tree.xpath("//div[@t-field='record.x_studio_image']")
        self.assertEqual(len(image_field), 1)
        self.assertEqual(image_field[0].get("t-options-widget"), "'image'")
        monetary_field = listing_tree.xpath("//span[@t-field='record.x_studio_monetary']")
        self.assertEqual(len(monetary_field), 1)

    def test_website_form(self):
        self.create_empty_app()

        pre_values_model = {
            "website_form_access": False,
            "website_form_key": False,
            "website_form_label": False,
        }

        for fname, val in pre_values_model.items():
            self.assertEqual(self.newModel[fname], val)

        view = self.env["ir.ui.view"].create({
            "arch": """
            <t t-name="website.website-studio-page">
                <t t-call="website.layout">
                    <div id="wrap" class="oe_structure">
                        <section class="s_website_form o_cc o_cc2 pt64 pb64 o_colored_level" data-vcss="001" data-snippet="s_website_form" data-name="Form">
                            <div class="o_container_small">
                                <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                                    <div class="row text-center">
                                        <div class="col-12 pb16 o_colored_level">
                                            <h2 class="o_default_snippet_text">Let's Connect</h2>
                                        </div>
                                    </div>
                                    <div class="s_website_form_rows row s_col_no_bgcolor">
                                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_dnone">
                                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px">
                                                    <span class="s_website_form_label_content"/>
                                                </label>
                                            <div class="col-sm"></div>
                                        </div>
                                    </div>
                                    <div class="mb-0 py-2 col-12 s_website_form_submit text-end s_website_form_no_submit_label" data-name="Submit Button">
                                            <div style="width: 200px;" class="s_website_form_label"/>
                                            <span id="s_website_form_result"/>
                                            <a href="#" role="button" class="btn btn-primary s_website_form_send o_default_snippet_text">Submit</a>
                                        </div>
                                    </div>
                                </form>
                            </div>
                        </section>
                    </div>
                </t>
            </t>""",
            "type": "qweb"
        })
        self.env["website.page"].create({
            "url": "/website-studio-page",
            "view_id": view.id,
        })

        self.start_tour("/@/website-studio-page", 'website_studio_website_form', login="admin", timeout=3600)
        post_values_model = {
            "website_form_access": True,
            "website_form_key": f"website_studio.{self.newModel.model}",
            "website_form_label": f"Create {self.newModel.name}",
        }
        for fname, val in post_values_model.items():
            self.assertEqual(self.newModel[fname], val)

        cow_view = self.env["ir.ui.view"].search([("key", "=", view.key), ("id", "not in", view.ids)])
        view_tree = etree.fromstring(cow_view.arch)
        form = view_tree.xpath("//form")[0]
        self.assertEqual(form.get("data-model_name"), self.newModel.model)

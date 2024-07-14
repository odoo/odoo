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
            "type": "tree",
            "arch": '''
                <tree>
                    <field name="x_name" />
                    <field name="x_studio_currency_id"/>
                    <field name="x_studio_monetary"/>
                    <field name="x_studio_tag_ids"/>
                </tree>
            '''
        })

        self.newAction = self.env["ir.actions.act_window"].create({
            "name": "simple model",
            "res_model": "x_test_model",
            "view_ids": [Command.create({"view_id": self.listView.id, "view_mode": "tree"}), Command.create({"view_id": self.formView.id, "view_mode": "form"})],
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

        self.start_tour("/web", 'website_studio_listing_and_page', login="admin", timeout=3600)
        created_pages = self.env["website.controller.page"].search([])
        self.assertEqual(len(created_pages), 2)
        self.assertEqual(created_pages[0].name_slugified, 'mycustom-name')
        self.assertEqual(len(created_pages[0].menu_ids), 1)
        self.assertEqual(len(created_pages[0].view_id), 1)
        self.assertEqual(created_pages[0].page_type, 'listing')

        self.assertEqual(created_pages[1].name_slugified, 'mycustom-name')
        self.assertEqual(len(created_pages[1].menu_ids), 0)
        self.assertEqual(len(created_pages[1].view_id), 1)
        self.assertEqual(created_pages[1].page_type, 'single')

        listing_tree = etree.fromstring(created_pages[0].view_id.arch)
        name_field = listing_tree.xpath("//span[@t-field='record.display_name']")
        self.assertEqual(len(name_field), 1)
        tag_loop = listing_tree.xpath("//t[@t-foreach='record.x_studio_tag_ids']")
        self.assertEqual(len(tag_loop), 1)
        tag_field = listing_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = listing_tree.xpath("//img[@t-attf-src='data:image/png;base64,{{record.x_studio_image}}']")
        self.assertEqual(len(image_field), 1)
        monetary_field = listing_tree.xpath("//span[@t-field='record.x_studio_monetary']")
        self.assertEqual(len(monetary_field), 1)

        page_tree = etree.fromstring(created_pages[1].view_id.arch)
        name_field = page_tree.xpath("//span[@t-field='record.display_name']")
        self.assertEqual(len(name_field), 2)
        tag_field = page_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = page_tree.xpath("//img[@t-attf-src='data:image/png;base64,{{record.x_studio_image}}']")
        self.assertEqual(len(image_field), 1)
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

        self.start_tour("/web", 'website_studio_listing_without_page', login="admin", watch=False, timeout=3600)
        created_pages = self.env["website.controller.page"].search([])
        self.assertEqual(len(created_pages), 1)
        self.assertEqual(created_pages[0].name_slugified, 'mycustom-name')
        self.assertEqual(len(created_pages[0].menu_ids), 1)
        self.assertEqual(len(created_pages[0].view_id), 1)
        self.assertEqual(created_pages[0].page_type, 'listing')

        listing_tree = etree.fromstring(created_pages[0].view_id.arch)
        name_field = listing_tree.xpath("//span[@t-field='record.display_name']")
        self.assertEqual(len(name_field), 1)
        tag_loop = listing_tree.xpath("//t[@t-foreach='record.x_studio_tag_ids']")
        self.assertEqual(len(tag_loop), 1)
        tag_field = listing_tree.xpath("//span[@t-field='tag.display_name']")
        self.assertEqual(len(tag_field), 1)
        image_field = listing_tree.xpath("//img[@t-attf-src='data:image/png;base64,{{record.x_studio_image}}']")
        self.assertEqual(len(image_field), 1)
        monetary_field = listing_tree.xpath("//span[@t-field='record.x_studio_monetary']")
        self.assertEqual(len(monetary_field), 1)

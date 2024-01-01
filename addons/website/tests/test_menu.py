# coding: utf-8

import json

from hashlib import sha256
from lxml import html

from odoo.tests import common


class TestMenu(common.TransactionCase):
    def setUp(self):
        super(TestMenu, self).setUp()
        self.nb_website = self.env['website'].search_count([])

    def test_01_menu_got_duplicated(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        self.menu_root = Menu.create({
            'name': 'Root',
        })

        self.menu_child = Menu.create({
            'name': 'Child',
            'parent_id': self.menu_root.id,
        })

        self.assertEqual(total_menu_items + self.nb_website * 2, Menu.search_count([]), "Creating a menu without a website_id should create this menu for every website_id")

    def test_02_menu_count(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        top_menu = self.env['website'].get_current_website().menu_id
        data = [
            {
                'id': 'new-1',
                'parent_id': top_menu.id,
                'name': 'New Menu Specific 1',
                'url': '/new-specific-1',
                'is_mega_menu': False,
            },
            {
                'id': 'new-2',
                'parent_id': top_menu.id,
                'name': 'New Menu Specific 2',
                'url': '/new-specific-2',
                'is_mega_menu': False,
            }
        ]
        Menu.save(1, {'data': data, 'to_delete': []})

        self.assertEqual(total_menu_items + 2, Menu.search_count([]), "Creating 2 new menus should create only 2 menus records")

    def test_03_default_menu_for_new_website(self):
        Website = self.env['website']
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        # Simulating website.menu created on module install (blog, shop, forum..) that will be created on default menu tree
        default_menu = self.env.ref('website.main_menu')
        Menu.create({
            'name': 'Sub Default Menu',
            'parent_id': default_menu.id,
        })
        self.assertEqual(total_menu_items + 1 + self.nb_website, Menu.search_count([]), "Creating a default child menu should create it as such and copy it on every website")

        # Ensure new website got a top menu
        total_menus = Menu.search_count([])
        Website.create({'name': 'new website'})
        self.assertEqual(total_menus + 4, Menu.search_count([]), "New website's bootstraping should have duplicate default menu tree (Top/Home/Contactus/Sub Default Menu)")

    def test_04_specific_menu_translation(self):
        IrModuleModule = self.env['ir.module.module']
        if self.env['website'].search_count([]) == 1:
            self.env['website'].create({
                'name': 'My Website 2',
                'domain': '',
                'sequence': 20,
            })

        Menu = self.env['website.menu']
        existing_menus = Menu.search([])

        default_menu = self.env.ref('website.main_menu')
        template_menu = Menu.create({
            'parent_id': default_menu.id,
            'name': 'Menu in english',
            'url': 'turlututu',
        })
        new_menus = Menu.search([]) - existing_menus
        specific1, specific2 = new_menus.with_context(lang='fr_FR') - template_menu

        # create fr_FR translation for template menu
        self.env.ref('base.lang_fr').active = True
        template_menu.with_context(lang='fr_FR').name = 'Menu en français'
        self.assertEqual(specific1.name, 'Menu in english',
                         'Translating template menu does not translate specific menu')

        # have different translation for specific website
        specific1.name = 'Menu in french'

        # loading translation add missing specific translation
        IrModuleModule._load_module_terms(['website'], ['fr_FR'])
        Menu.invalidate_model(['name'])
        self.assertEqual(specific1.name, 'Menu in french',
                         'Load translation without overwriting keep existing translation')
        self.assertEqual(specific2.name, 'Menu en français',
                         'Load translation add missing translation from template menu')

        # loading translation with overwrite sync all translations from menu template
        IrModuleModule._load_module_terms(['website'], ['fr_FR'], overwrite=True)
        Menu.invalidate_model(['name'])
        self.assertEqual(specific1.name, 'Menu en français',
                         'Load translation with overwriting update existing menu from template')

    def test_05_default_menu_unlink(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        default_menu = self.env.ref('website.main_menu')
        default_menu.child_id[0].unlink()
        self.assertEqual(total_menu_items - 1 - self.nb_website, Menu.search_count([]), "Deleting a default menu item should delete its 'copies' (same URL) from website's menu trees. In this case, the default child menu and its copies on website 1 and website 2")


class TestMenuHttp(common.HttpCase):
    def setUp(self):
        super().setUp()
        self.page_url = '/page_specific'
        self.page = self.env['website.page'].create({
            'url': self.page_url,
            'website_id': 1,
            # ir.ui.view properties
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Specific View</div>',
            'key': 'test.specific_view',
        })
        self.menu = self.env['website.menu'].create({
            'name': 'Page Specific menu',
            'page_id': self.page.id,
            'url': self.page_url,
            'website_id': 1,
        })

    def simulate_rpc_save_menu(self, data, to_delete=None):
        self.authenticate("admin", "admin")
        # `Menu.save(1, {'data': [data], 'to_delete': []})` would have been
        # ideal but need a full frontend context to generate routing maps,
        # router and registry, even MockRequest is not enough
        self.url_open('/web/dataset/call_kw', data=json.dumps({
            "params": {
                'model': 'website.menu',
                'method': 'save',
                'args': [1, {'data': [data], 'to_delete': to_delete or []}],
                'kwargs': {},
            },
        }), headers={"Content-Type": "application/json", "Referer": self.page.get_base_url() + self.page_url})

    def test_01_menu_page_m2o(self):
        # Ensure that the M2o relation tested later in the test is properly set.
        self.assertTrue(self.menu.page_id, "M2o should have been set by the setup")
        # Edit the menu URL to a 'reserved' URL
        data = {
            'id': self.menu.id,
            'parent_id': self.menu.parent_id.id,
            'name': self.menu.name,
            'url': '/website/info',
        }
        self.simulate_rpc_save_menu(data)

        self.assertFalse(self.menu.page_id, "M2o should have been unset as this is a reserved URL.")
        self.assertEqual(self.menu.url, '/website/info', "Menu URL should have changed.")
        self.assertEqual(self.page.url, self.page_url, "Page's URL shouldn't have changed.")

        # 3. Edit the menu URL back to the page URL
        data['url'] = self.page_url
        self.env['website.menu'].save(1, {'data': [data], 'to_delete': []})
        self.assertEqual(self.menu.page_id, self.page,
                         "M2o should have been set back, as there was a page found with the new URL set on the menu.")
        self.assertTrue(self.page.url == self.menu.url == self.page_url)

    def test_02_menu_anchors(self):
        # Ensure that the M2o relation tested later in the test is properly set.
        self.assertTrue(self.menu.page_id, "M2o should have been set by the setup")
        # Edit the menu URL to an anchor
        data = {
            'id': self.menu.id,
            'parent_id': self.menu.parent_id.id,
            'name': self.menu.name,
            'url': '#anchor',
        }
        self.simulate_rpc_save_menu(data)
        self.assertFalse(self.menu.page_id, "M2o should have been unset as this is an anchor URL.")
        self.assertEqual(self.menu.url, self.page_url + '#anchor', "Page URL should have been properly prefixed with the referer url")
        self.assertEqual(self.page.url, self.page_url, "Page URL should not have changed")

    def test_03_mega_menu_translate(self):
        # Setup
        fr = self.env['res.lang']._activate_lang('fr_FR')
        Menu = self.env['website.menu']
        website = self.env['website'].browse(1)
        website.language_ids += fr
        menu = Menu.create({
            'name': 'Test Mega Menu Content Translation Edit Mode',
            'mega_menu_content': '<p>something</p>',
            'parent_id': website.menu_id.id,
            'website_id': website.id,
        })
        self.env['ir.module.module']._load_module_terms(['website'], [fr.code])

        # Load cache
        self.url_open('/%s' % fr.url_code)
        self.url_open('/%s?edit_translations=1' % fr.url_code)

        # Translate
        root = html.fromstring(menu.mega_menu_content)
        to_translate = root.text_content()
        sha = sha256(to_translate.encode()).hexdigest()
        menu.update_field_translations_sha('mega_menu_content', {fr.code: {sha: 'french_mega_menu_content'}})
        self.assertIn("french_mega_menu_content",
                      menu.with_context(lang=fr.code, website_id=website.id).mega_menu_content)

        # Checks
        page = self.url_open('/%s' % fr.url_code)
        self.assertIn(b"french_mega_menu_content", page.content)
        page = self.url_open('/%s?edit_translations=1' % fr.url_code)
        self.assertIn(b"french_mega_menu_content", page.content)

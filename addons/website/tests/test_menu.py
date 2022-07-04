# coding: utf-8

import json

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
    def test_01_menu_page_m2o(self):
        # 1. Create a page with a menu
        Menu = self.env['website.menu']
        Page = self.env['website.page']
        page_url = '/page_specific'
        page = Page.create({
            'url': page_url,
            'website_id': 1,
            # ir.ui.view properties
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Specific View</div>',
            'key': 'test.specific_view',
        })
        menu = Menu.create({
            'name': 'Page Specific menu',
            'page_id': page.id,
            'url': page_url,
            'website_id': 1,
        })

        # 2. Edit the menu URL to a 'reserved' URL
        data = {
            'id': menu.id,
            'parent_id': menu.parent_id.id,
            'name': menu.name,
            'url': '/website/info',
        }
        self.authenticate("admin", "admin")
        # `Menu.save(1, {'data': [data], 'to_delete': []})` would have been
        # ideal but need a full frontend context to generate routing maps,
        # router and registry, even MockRequest is not enough
        self.url_open('/web/dataset/call_kw', data=json.dumps({
            "params": {
                'model': 'website.menu',
                'method': 'save',
                'args': [1, {'data': [data], 'to_delete': []}],
                'kwargs': {},
            },
        }), headers={"Content-Type": "application/json"})

        self.assertFalse(menu.page_id, "M2o should have been unset as this is a reserved URL.")
        self.assertEqual(menu.url, '/website/info', "Menu URL should have changed.")
        self.assertEqual(page.url, page_url, "Page's URL shouldn't have changed.")

        # 3. Edit the menu URL back to the page URL
        data['url'] = page_url
        Menu.save(1, {'data': [data], 'to_delete': []})
        self.assertEqual(menu.page_id, page,
                         "M2o should have been set back, as there was a page found with the new URL set on the menu.")
        self.assertTrue(page.url == menu.url == page_url)

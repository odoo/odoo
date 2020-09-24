# coding: utf-8
from odoo.tests import common


class TestMenu(common.TransactionCase):

    def test_menu_got_duplicated(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        self.menu_root = Menu.create({
            'name': 'Root',
        })

        self.menu_child = Menu.create({
            'name': 'Child',
            'parent_id': self.menu_root.id,
        })

        self.assertEqual(total_menu_items + 4, Menu.search_count([]), "Creating a menu without a website_id should create this menu for every website_id")

    def test_menu_count(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        top_menu = self.env['website'].get_current_website().menu_id
        data = [
            {
                'id': 'new-1',
                'parent_id': top_menu.id,
                'name': 'New Menu Specific 1',
                'url': '/new-specific-1',
            },
            {
                'id': 'new-2',
                'parent_id': top_menu.id,
                'name': 'New Menu Specific 2',
                'url': '/new-specific-2',
            }
        ]
        Menu.save(1, {'data': data, 'to_delete': []})

        self.assertEqual(total_menu_items + 2, Menu.search_count([]), "Creating 2 new menus should create only 2 menus records")

    def test_default_menu_for_new_website(self):
        Website = self.env['website']
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        # Simulating website.menu created on module install (blog, shop, forum..) that will be created on default menu tree
        default_menu = self.env.ref('website.main_menu')
        Menu.create({
            'name': 'Sub Default Menu',
            'parent_id': default_menu.id,
        })
        self.assertEqual(total_menu_items + 3, Menu.search_count([]), "Creating a default child menu should create it as such and copy it on every website")

        # Ensure new website got a top menu
        total_menus = Menu.search_count([])
        Website.create({'name': 'new website'})
        self.assertEqual(total_menus + 4, Menu.search_count([]), "New website's bootstraping should have duplicate default menu tree (Top/Home/Contactus/Sub Default Menu)")

    def test_specific_menu_translation(self):
        Translation = self.env['ir.translation']
        Website = self.env['website']
        Menu = self.env['website.menu']
        existing_menus = Menu.search([])

        default_menu = self.env.ref('website.main_menu')
        template_menu = Menu.create({
            'parent_id': default_menu.id,
            'name': 'Menu in english',
            'url': 'turlututu',
        })
        new_menus =  Menu.search([]) - existing_menus
        specific1, specific2 = new_menus.with_context(lang='fr_FR') - template_menu

        # create fr_FR translation for template menu
        self.env.ref('base.lang_fr').active = True
        template_menu.with_context(lang='fr_FR').name = 'Menu en français'
        Translation.search([
            ('name', '=', 'website.menu,name'), ('res_id', '=', template_menu.id),
        ]).module = 'website'
        self.assertEquals(specific1.name,  'Menu in english',
            'Translating template menu does not translate specific menu')

        # have different translation for specific website
        specific1.name = 'Menu in french'

        # loading translation add missing specific translation
        Translation.load_module_terms(['website'], ['fr_FR'])
        Menu.invalidate_cache(['name'])
        self.assertEquals(specific1.name,  'Menu in french',
            'Load translation without overwriting keep existing translation')
        self.assertEquals(specific2.name,  'Menu en français',
            'Load translation add missing translation from template menu')

        # loading translation with overwrite sync all translations from menu template
        Translation.with_context(overwrite=True).load_module_terms(['website'], ['fr_FR'])
        Menu.invalidate_cache(['name'])
        self.assertEquals(specific1.name,  'Menu en français',
            'Load translation with overwriting update existing menu from template')

    def test_default_menu_unlink(self):
        Menu = self.env['website.menu']
        total_menu_items = Menu.search_count([])

        default_menu = self.env.ref('website.main_menu')
        default_menu.child_id[0].unlink()
        self.assertEqual(total_menu_items - 3, Menu.search_count([]), "Deleting a default menu item should delete its 'copies' (same URL) from website's menu trees. In this case, the default child menu and its copies on website 1 and website 2")

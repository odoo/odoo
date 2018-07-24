# coding: utf-8
from odoo.tests import common


class TestMenu(common.TransactionCase):

    def test_website_own_menu_container(self):
        Website = self.env['website']
        Menu = self.env['website.menu']

        total_menus = Menu.search_count([])
        Website.create({'name': 'new website'})
        self.assertEqual(total_menus + 2, Menu.search_count([]), "New website's bootstraping should have created a container menu and home menu")

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

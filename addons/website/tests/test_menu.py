# coding: utf-8
from odoo.tests import common


class TestMenu(common.TransactionCase):
    def setUp(self):
        super(TestMenu, self).setUp()
        Menu = self.env['website.menu']

        self.menu_root = Menu.create({
            'name': 'Root',
        })

        self.menu_child = Menu.create({
            'name': 'Child',
            'parent_id': self.menu_root.id,
        })

        self.menu_leaf1 = Menu.create({
            'name': 'Leaf 1',
            'parent_id': self.menu_child.id,
        })

        self.menu_leaf2 = Menu.create({
            'name': 'Leaf 2',
            'parent_id': self.menu_root.id,
        })

    def test_cow_leaf(self):
        Menu = self.env['website.menu']

        # backend write, no COW
        total_menu_items = Menu.search_count([])
        self.menu_leaf1.write({'name': 'Leaf 1 modified'})
        self.assertEqual(total_menu_items, Menu.search_count([]))

        # write through website 1
        self.menu_leaf1.with_context(website_id=1).write({'name': 'Leaf 1 Website 1'})
        self.assertEqual(self.menu_leaf1.name, 'Leaf 1 modified')
        self.assertEqual(total_menu_items + 1, Menu.search_count([]))
        new_menu = Menu.search([('name', '=', 'Leaf 1 Website 1')])
        self.assertEqual(new_menu.website_id.id, 1)

    def test_cow_root(self):
        Menu = self.env['website.menu']

        # backend write, no COW
        total_menu_items = Menu.search_count([])
        self.menu_root.write({'name': 'Root 1 modified'})
        self.assertEqual(total_menu_items, Menu.search_count([]))

        # write through website 1
        self.menu_root.with_context(website_id=1).write({'name': 'Root Website 1'})
        self.assertEqual(self.menu_root.name, 'Root 1 modified')
        self.assertEqual(total_menu_items + 4, Menu.search_count([]))

        # verify parent/child structure
        website_specific_leaf2 = Menu.search([('name', '=', 'Leaf 2'), ('website_id', '=', 1)])
        website_specific_leaf1 = Menu.search([('name', '=', 'Leaf 1'), ('website_id', '=', 1)])
        website_specific_child = Menu.search([('name', '=', 'Child'), ('website_id', '=', 1)])
        website_specific_root = Menu.search([('name', '=', 'Root Website 1'), ('website_id', '=', 1)])
        self.assertEqual(website_specific_leaf2.parent_id.id, website_specific_root.id)
        self.assertEqual(website_specific_leaf1.parent_id.id, website_specific_child.id)
        self.assertEqual(website_specific_child.parent_id.id, website_specific_root.id)

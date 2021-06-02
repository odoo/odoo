# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestMenu(TransactionCase):

    def test_00_menu_deletion(self):
        """Verify that menu deletion works properly when there are child menus, and those
           are indeed made orphans"""
        Menu = self.env['ir.ui.menu']
        root = Menu.create({'name': 'Test root'})
        child1 = Menu.create({'name': 'Test child 1', 'parent_id': root.id})
        child2 = Menu.create({'name': 'Test child 2', 'parent_id': root.id})
        child21 = Menu.create({'name': 'Test child 2-1', 'parent_id': child2.id})
        all_ids = [root.id, child1.id, child2.id, child21.id]

        # delete and check that direct children are promoted to top-level
        # cfr. explanation in menu.unlink()
        root.unlink()

        # Generic trick necessary for search() calls to avoid hidden menus 
        Menu = self.env['ir.ui.menu'].with_context({'ir.ui.menu.full_list': True})

        remaining = Menu.search([('id', 'in', all_ids)], order="id")
        self.assertEqual([child1.id, child2.id, child21.id], remaining.ids)

        orphans =  Menu.search([('id', 'in', all_ids), ('parent_id', '=', False)], order="id")
        self.assertEqual([child1.id, child2.id], orphans.ids)

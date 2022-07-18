# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock

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

    def test_best_root_menu_for_model(self):
        Menu = self.env['ir.ui.menu']
        Action = self.env['ir.actions.act_window']

        def _new_menu(name, parent_id=None, action=None):
            inst = Menu.create({'name': name, 'parent_id': parent_id})
            if action:
                inst.action = action
            return inst

        new_menu = Mock(side_effect=_new_menu)

        def new_action(name, res_model, view_mode=None, domain=None, context=None):
            return Action.create({
                'name': name,
                'res_model': res_model,
                'view_mode': view_mode,
                'domain': domain,
                'context': context or {},
                'type': 'ir.actions.act_window',
            })

        # Remove all menus and setup test menu with known results
        Menu.search([]).unlink()

        menu_root_invoicing = new_menu('Invoicing')
        menu_invoicing_customer = new_menu('Customers', parent_id=menu_root_invoicing.id)
        new_menu('Customers', parent_id=menu_invoicing_customer.id,
                 action=new_action('Customers', res_model='res.partner', view_mode='kanban,tree,form',
                                   context="""{
                                       'search_default_customer': 1,
                                       'res_partner_search_mode': 'customer', 
                                       'default_is_company': True, 
                                       'default_customer_rank': 1
                                   }"""))
        menu_root_contact = new_menu('Contacts')
        new_menu('Contacts', parent_id=menu_root_contact.id,
                 action=new_action('Contacts', res_model='res.partner', view_mode='kanban,tree,form,activity',
                                   context="{'default_is_company': "+(' '*1000)+"True"+('\n'*1000)+"}", domain='[]'))
        menu_root_sales = new_menu('Sales')
        menu_sales_orders = new_menu('Orders', parent_id=menu_root_sales.id)
        new_menu('Customers', parent_id=menu_sales_orders.id,
                 action=new_action('Customers', res_model='res.partner', view_mode='kanban,tree,form',
                                   context="""{
                                            'search_default_customer': 1,
                                            'res_partner_search_mode': 'customer', 
                                            'default_is_company': True, 
                                            'default_customer_rank': 1
                                        }"""))
        menu_root_settings = new_menu('Settings')
        menu_settings_user_and_companies = new_menu('Users & Companies', parent_id=menu_root_settings.id)
        new_menu('Companies', parent_id=menu_settings_user_and_companies.id,
                 action=new_action('Companies', res_model='res.company', view_mode='tree,kanban,form'))

        self.assertEqual(len(Menu._visible_menu_ids()), new_menu.call_count)
        self.assertEqual(Menu._get_best_menu_root_for_model('res.partner'), menu_root_contact.id)
        self.assertEqual(Menu._get_best_menu_root_for_model('res.bank'), None)
        self.assertEqual(Menu._get_best_menu_root_for_model('res.company'), menu_root_settings.id)

        self.registry.reset_changes()

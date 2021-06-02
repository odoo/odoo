# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestViewsDuringModuleOperation(TransactionCase):
    def test_01_cow_views_unlink_on_module_update(self):
        """ Ensure COW views are correctly removed during module update.
        Not removing the view could lead to traceback:
        - Having a view A
        - Having a view B that inherits from a view C
        - View B t-call view A
        - COW view B
        - Delete view A and B from module datas and update it
        - Rendering view C will crash since it will render child view B that
          t-call unexisting view A
        """

        View = self.env['ir.ui.view']
        Imd = self.env['ir.model.data']

        update_module_base_view = self.env.ref('test_website.update_module_base_view')
        update_module_view_to_be_t_called = View.create({
            'name': 'View to be t-called',
            'type': 'qweb',
            'arch': '<div>I will be t-called</div>',
            'key': 'test_website.update_module_view_to_be_t_called',
        })
        update_module_child_view = View.create({
            'name': 'Child View',
            'mode': 'extension',
            'inherit_id': update_module_base_view.id,
            'arch': '''
                <div position="inside">
                    <t t-call="test_website.update_module_view_to_be_t_called"/>
                </div>
            ''',
            'key': 'test_website.update_module_child_view',
        })

        # Create IMD so when updating the module the views will be removed (not found in file)
        Imd.create({
            'module': 'test_website',
            'name': 'update_module_view_to_be_t_called',
            'model': 'ir.ui.view',
            'res_id': update_module_view_to_be_t_called.id,
        })
        Imd.create({
            'module': 'test_website',
            'name': 'update_module_child_view',
            'model': 'ir.ui.view',
            'res_id': update_module_child_view.id,
        })

        # Trigger COW on child view
        update_module_child_view.with_context(website_id=1).write({'name': 'Child View (W1)'})

        # Ensure views are correctly setup
        self.assertEquals(View.search_count([('type', '=', 'qweb'), ('key', '=', update_module_child_view.key)]), 2)
        self.assertTrue(self.env.ref(update_module_view_to_be_t_called.key))
        self.assertTrue(self.env.ref(update_module_base_view.key))

        # Update the module
        test_website_module = self.env['ir.module.module'].search([('name', '=', 'test_website')])
        test_website_module.button_immediate_upgrade()

        # Ensure generic views got removed
        self.assertFalse(self.env.ref('test_website.update_module_view_to_be_t_called', raise_if_not_found=False))
        # Ensure specific COW views got removed
        self.assertEquals(View.search_count([('type', '=', 'qweb'), ('key', '=', 'test_website.update_module_child_view')]), 0)

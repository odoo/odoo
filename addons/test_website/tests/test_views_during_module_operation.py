# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import standalone


@standalone('cow_views')
def test_01_cow_views_unlink_on_module_update(env):
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

    View = env['ir.ui.view']
    Imd = env['ir.model.data']

    update_module_base_view = env.ref('test_website.update_module_base_view')
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
    msg = "View '%s' does not exist!"
    assert View.search_count([
        ('type', '=', 'qweb'),
        ('key', '=', update_module_child_view.key)
    ]) == 2, msg % update_module_child_view.key
    assert bool(env.ref(update_module_view_to_be_t_called.key)),\
        msg % update_module_view_to_be_t_called.key
    assert bool(env.ref(update_module_base_view.key)), msg % update_module_base_view.key

    # Upgrade the module
    test_website_module = env['ir.module.module'].search([('name', '=', 'test_website')])
    test_website_module.button_immediate_upgrade()
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    # Ensure generic views got removed
    view = env.ref('test_website.update_module_view_to_be_t_called', raise_if_not_found=False)
    assert not view, "Generic view did not get removed!"

    # Ensure specific COW views got removed
    assert not env['ir.ui.view'].search_count([
        ('type', '=', 'qweb'),
        ('key', '=', 'test_website.update_module_child_view'),
    ]), "Specific COW views did not get removed!"

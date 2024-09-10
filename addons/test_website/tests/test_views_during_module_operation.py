# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.tests import standalone


@standalone('cow_views', 'website_standalone')
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
    env.transaction.reset()     # clear the set of environments

    # Ensure generic views got removed
    view = env.ref('test_website.update_module_view_to_be_t_called', raise_if_not_found=False)
    assert not view, "Generic view did not get removed!"

    # Ensure specific COW views got removed
    assert not env['ir.ui.view'].search_count([
        ('type', '=', 'qweb'),
        ('key', '=', 'test_website.update_module_child_view'),
    ]), "Specific COW views did not get removed!"


@standalone('theme_views', 'website_standalone')
def test_02_copy_ids_views_unlink_on_module_update(env):
    """ Ensure copy_ids views are correctly removed during module update.
    - Having an ir.ui.view A in the codebase, eg `website.layout`
    - Having a theme.ir.ui.view B in a theme, inheriting ir.ui.view A
    - Removing the theme.ir.ui.view B from the XML file and then updating the
      theme for a particular website should:
      1. Remove the theme.ir.ui.view record, which is the record pointed by the
         ir.model.data
         -> This is done through the regular Odoo behavior related to the
            ir.model.data and XML file check on upgrade.
      2. Remove the theme.ir.ui.view's copy_ids (sort of the COW views)
         -> Not working for now
      3. (not impact other website using this theme, see below)
         -> This is done through odoo/odoo@96ef4885a79 but did not come with
            tests

      Point 2. was not working, this test aims to ensure it will now.
      Note: This can't be done through a `ondelete=cascade` as this would
            impact other websites when modifying a specific website. This would
            be against the multi-website rule:
            "What is done on a website should not alter other websites."

            Regarding the flow described above, if a theme module was updated
            through the command line (or via the UI, but this is not possible in
            standard as theme modules are hidden from the Apps), it should
            update every website using this theme.
    """
    View = env['ir.ui.view']
    ThemeView = env['theme.ir.ui.view']
    Imd = env['ir.model.data']

    website_1 = env['website'].browse(1)
    website_2 = env['website'].browse(2)
    theme_default = env.ref('base.module_theme_default')

    # Install theme_default on website 1 and website 2
    (website_1 + website_2).theme_id = theme_default
    env['ir.module.module'].with_context(load_all_views=True)._theme_load(website_1)
    env['ir.module.module'].with_context(load_all_views=True)._theme_load(website_2)

    key = 'theme_default.theme_child_view'
    domain = [
        ('type', '=', 'qweb'),
        ('key', '=', key),
    ]

    def _simulate_xml_view():
        # Simulate a theme.ir.ui.view inside theme_default XML files
        base_view = env.ref('test_website.update_module_base_view')
        theme_child_view = ThemeView.create({
            'name': 'Theme Child View',
            'mode': 'extension',
            'inherit_id': f'{base_view._name},{base_view.id}',
            'arch': '''
                <div position="inside">
                    <p>, and I am inherited by a theme.ir.ui.view</p>
                </div>
            ''',
            'key': key,
        })
        # Create IMD so when updating the module the views will be removed (not found in file)
        Imd.create({
            'module': 'theme_default',
            'name': 'theme_child_view',
            'model': 'theme.ir.ui.view',
            'res_id': theme_child_view.id,
        })
        # Simulate the theme.ir.ui.view being installed on website 1 and 2
        View.create([
            theme_child_view._convert_to_base_model(website_1),
            theme_child_view._convert_to_base_model(website_2),
        ])

        # Ensure views are correctly setup: the theme.ir.ui.view should have been
        # copied to an ir.ui.view for website 1
        view_website_1, view_website_2 = View.search(domain + [
            ('theme_template_id', '=', theme_child_view.id),
            ('website_id', 'in', (website_1 + website_2).ids),
        ])
        assert (
            set((view_website_1 + view_website_2)).issubset(theme_child_view.copy_ids)
            and view_website_1.website_id == website_1
            and view_website_2.website_id == website_2
        ), "Theme View should have been copied to the website."

        return view_website_1, view_website_2, theme_child_view

    ##########################################
    # CASE 1: generic update (-u, migration) #
    ##########################################

    view_website_1, view_website_2, theme_child_view = _simulate_xml_view()

    # Upgrade the module
    theme_default.button_immediate_upgrade()
    env.transaction.reset()  # clear the set of environments

    # Ensure the theme.ir.ui.view got removed (since there is an IMD but not
    # present in XML files)
    view = env.ref('theme_default.theme_child_view', raise_if_not_found=False)
    assert not view, "Theme view should have been removed during module update."
    assert not theme_child_view.exists(),\
        "Theme view should have been removed during module update. (2)"

    # Ensure copy_ids view got removed (and is not a leftover orphan)
    assert not View.search(domain), "copy_ids views did not get removed!"
    assert not (view_website_1.exists() or view_website_2.exists()),\
        "copy_ids views did not get removed! (2)"

    #####################################################
    # CASE 2: specific update (website theme selection) #
    #####################################################

    view_website_1, view_website_2, theme_child_view = _simulate_xml_view()

    # Upgrade the module
    with MockRequest(env, website=website_1):
        theme_default.button_immediate_upgrade()
    env.transaction.reset()  # clear the set of environments

    # Ensure the theme.ir.ui.view got removed (since there is an IMD but not
    # present in XML files)
    view = env.ref('theme_default.theme_child_view', raise_if_not_found=False)
    assert not view, "Theme view should have been removed during module update."
    assert not theme_child_view.exists(),\
        "Theme view should have been removed during module update. (2)"

    # Ensure only website_1 copy_ids got removed, website_2 should be untouched
    assert not view_website_1.exists() and view_website_2.exists(),\
        "Only website_1 copy should be removed (2)"

# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" This test ensure `inherit_id` update is correctly replicated on cow views.
The view receiving the `inherit_id` update is either:
1. in a module loaded before `website`. In that case, `website` code is not
   loaded yet, so we store the updates to replay the changes on the cow views
   once `website` module is loaded (see `_check()`). This test is testing that
   part.
2. in a module loaded after `website`. In that case, the `inherit_id` update is
   directly replicated on the cow views. That behavior is tested with
   `test_module_new_inherit_view_on_parent_already_forked` and
   `test_specific_view_module_update_inherit_change` in `website` module.
"""

from odoo.tests import standalone


@standalone('cow_views_inherit', 'website_standalone')
def test_01_cow_views_inherit_on_module_update(env):
    #     A    B                        A    B
    #    / \                   =>           / \
    #   D   D'                             D   D'

    # 1. Setup hierarchy as comment above
    View = env['ir.ui.view']
    View.with_context(_force_unlink=True, active_test=False).search([('website_id', '=', 1)]).unlink()
    child_view = env.ref('portal.footer_language_selector')
    parent_view = env.ref('portal.portal_back_in_edit_mode')
    # Remove any possibly existing COW view (another theme etc)
    parent_view.with_context(_force_unlink=True, active_test=False)._get_specific_views().unlink()
    child_view.with_context(_force_unlink=True, active_test=False)._get_specific_views().unlink()
    # Change `inherit_id` so the module update will set it back to the XML value
    child_view.write({'inherit_id': parent_view.id, 'arch': child_view.arch_db.replace('o_footer_copyright_name', 'text-center')})
    # Trigger COW on view
    child_view.with_context(website_id=1).write({'name': 'COW Website 1'})
    child_cow_view = child_view._get_specific_views()

    # 2. Ensure setup is as expected
    assert len(child_cow_view.inherit_id) == 1, "Should only be the XML view and its COW counterpart."
    assert child_cow_view.inherit_id == parent_view, "Ensure test is setup as expected."

    # 3. Upgrade the module
    portal_module = env['ir.module.module'].search([('name', '=', 'portal')])
    portal_module.button_immediate_upgrade()
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    # 4. Ensure cow view also got its inherit_id updated
    expected_parent_view = env.ref('portal.frontend_layout')  # XML data
    assert child_view.inherit_id == expected_parent_view, "Generic view security check."
    assert child_cow_view.inherit_id == expected_parent_view, "COW view should also have received the `inherit_id` update."


@standalone('cow_views_inherit', 'website_standalone')
def test_02_cow_views_inherit_on_module_update(env):
    #     A    B    B'                  A    B   B'
    #    / \                   =>            |   |
    #   D   D'                               D   D'

    # 1. Setup hierarchy as comment above
    View = env['ir.ui.view']
    View.with_context(_force_unlink=True, active_test=False).search([('website_id', '=', 1)]).unlink()
    view_D = env.ref('portal.my_account_link')
    view_A = env.ref('portal.message_thread')
    # Change `inherit_id` so the module update will set it back to the XML value
    view_D.write({'inherit_id': view_A.id, 'arch_db': view_D.arch_db.replace('o_logout_divider', 'discussion')})
    # Trigger COW on view
    view_B = env.ref('portal.user_dropdown')  # XML data
    view_D.with_context(website_id=1).write({'name': 'D Website 1'})
    view_B.with_context(website_id=1).write({'name': 'B Website 1'})
    view_Dcow = view_D._get_specific_views()

    # 2. Ensure setup is as expected
    view_Bcow = view_B._get_specific_views()
    assert view_Dcow.inherit_id == view_A, "Ensure test is setup as expected."
    assert len(view_Bcow) == len(view_Dcow) == 1, "Ensure test is setup as expected (2)."
    assert view_B != view_Bcow, "Security check to ensure `_get_specific_views` return what it should."

    # 3. Upgrade the module
    portal_module = env['ir.module.module'].search([('name', '=', 'portal')])
    portal_module.button_immediate_upgrade()
    env.reset()     # clear the set of environments
    env = env()     # get an environment that refers to the new registry

    # 4. Ensure cow view also got its inherit_id updated
    assert view_D.inherit_id == view_B, "Generic view security check."
    assert view_Dcow.inherit_id == view_Bcow, "COW view should also have received the `inherit_id` update."

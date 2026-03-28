
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.tests import standalone


@standalone('theme_upgrade', 'website_standalone')
def test_01_theme_upgrade_post_copy(env):
    """ This test ensures the theme `_post_copy()` method is only called when a
    theme is installed for the first time on a website and not when the theme is
    updated on that website.
    """
    # 1. Setup
    website = env['website'].search([], limit=1)
    Website = env['website'].with_context(website_id=website.id)

    # Get rid of as many website as we can, any website will drastically slows
    # down the test as when updating Theme Nano, it will update Theme Common
    # which is applied on every site having a theme. It will then update all
    # those websites.
    Website.get_test_themes_websites().unlink()
    for w in Website.search([('theme_id', '!=', False), ('id', '!=', website.id)]):
        try:
            w.unlink()
        except Exception:
            pass

    tfd_specific_view = Website.viewref('website.template_footer_descriptive')
    fls_specific_view = Website.viewref('portal.footer_language_selector')
    theme_nano_module = env.ref('base.module_theme_nano')

    def _simulate_user_manual_change():
        # Change some website options that will be changed by Theme Nano
        tfd_specific_view.active = False
        fls_specific_view.active = True

    # 2. Simulate some website option change made by the user
    _simulate_user_manual_change()

    # 3. Simulate user choosing a new theme for his website
    with MockRequest(env, website=website):
        theme_nano_module.with_context(website_id=website.id).button_choose_theme()

    assert Website.viewref('website.template_footer_descriptive').active is True, \
        "Theme Nano custo should be applied"
    assert Website.viewref('portal.footer_language_selector').active is False, \
        "Theme Nano custo should be applied (2)"

    # 4. Simulate some website option change made by the user, again
    _simulate_user_manual_change()

    # 5. Upgrade Theme Nano
    theme_nano_module.button_immediate_upgrade()
    env.transaction.reset()  # clear the set of environments

    assert Website.viewref('website.template_footer_descriptive').active is False, \
        "Theme Nano custo should NOT be applied"
    assert Website.viewref('portal.footer_language_selector').active is True, \
        "Theme Nano custo should NOT be applied (2)"

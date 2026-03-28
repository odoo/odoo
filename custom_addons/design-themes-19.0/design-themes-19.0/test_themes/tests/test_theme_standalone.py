# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.tests import standalone


@standalone('website_standalone')
def test_01_theme_install_generate_primary_templates(env):
    """ This test ensures the theme `_generate_primary_snippet_templates()`
    method is correctly called before xml views are generated.
    """
    # 1. Setup
    theme_buzzy = env.ref('base.module_theme_clean')

    if theme_buzzy.state == 'installed':
        theme_buzzy.button_immediate_uninstall()
    # Ensure those views are deleted to mimic the initial state of theme not installed.
    # Because "theme_buzzy" was installed before through "test_themes" dependencies, removing
    # those views is needed to replicate the bug: if the configurator views are not generated,
    # the theme install will fail because some of the imported views inherit them.
    env['ir.ui.view'].with_context(_force_unlink=True).search([('key', '=', 'website.configurator_s_banner')]).unlink()
    env['ir.ui.view'].with_context(_force_unlink=True).search([('key', '=', 'website.configurator_s_cover')]).unlink()
    theme_buzzy.button_immediate_install()


@standalone('website_standalone')
def test_02_theme_default_generate_primary_templates(env):

    def fake_website_api(self, path, payload):
        # Only the configurator custom_resources endpoint is used here
        assert path.startswith("/api/website/2/configurator/custom_resources")
        return {'images': {}}

    def fake_olg_api(self, path, payload):
        # Placeholder generator used by configurator
        assert path == "/api/olg/1/generate_placeholder"
        placeholders = payload.get("placeholders", [])
        mapping = {key: key for key in placeholders}
        return mapping

    # Verify that theme default's configurator templates are created
    # on website update.
    theme_default = env.ref('base.module_theme_default')
    website_module = env.ref('base.module_website')

    if theme_default.state == 'installed':
        theme_default.button_immediate_uninstall()
    env['ir.ui.view'].with_context(_force_unlink=True).search([('key', 'like', 'website.configurator_')]).unlink()

    with patch("odoo.addons.website.models.website.Website._website_api_rpc", autospec=True, side_effect=fake_website_api), \
         patch("odoo.addons.website.models.website.Website._OLG_api_rpc", autospec=True, side_effect=fake_olg_api):

        if website_module.state == 'installed':
            website_module.button_immediate_upgrade()
        else:
            website_module.button_immediate_install()

        template_keys = env['ir.ui.view'].search([('key', 'like', 'website.configurator')]).mapped('key')
        manifest = env['ir.module.module'].get_module_info('theme_default')
        snippets_per_page = manifest.get('configurator_snippets')
        for page in snippets_per_page:
            for snippet in snippets_per_page[page]:
                template_key = f'website.configurator_{page}_{snippet}'
                assert template_key in template_keys, f"{template_key} should exist"

        website = env['website'].search([], limit=1)
        website.ensure_one()
        with MockRequest(env, website=website):
            website.configurator_apply(
                selected_features=[1, 2, 3, 4],
                industry_id=2836,
                industry_name='private university',
                selected_palette='default-15',
                theme_name='theme_bewise',
                website_purpose='get_leads',
                website_type='business',
            )

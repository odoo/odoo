from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTheme(common.TransactionCase):

    def test_theme_remove_on_current_website(self):
        """This test ensure theme can be removed through the backend route."""
        website = self.env.ref('base.default_website')
        theme = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website.theme_id = theme

        theme.with_context(host_id=website.id).button_remove_theme()

        self.assertFalse(website.theme_id)

    def test_02_disable_view(self):
        """This test ensure only one template header can be active at a time."""
        website_id = self.env.ref('base.default_website')
        ThemeUtils = self.env['theme.utils'].with_context(website_id=website_id.id)

        ThemeUtils._reset_default_config()

        def _get_header_template_key():
            return self.env['ir.ui.view'].search([
                ('key', 'in', ThemeUtils._header_templates),
                ('website_id', '=', website_id.id),
            ]).key

        self.assertEqual(_get_header_template_key(), 'website.template_header_default',
                         "Only the default template should be active.")

        key = 'website.template_header_vertical'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Only one template can be active at a time.")

        key = 'website.template_header_hamburger'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Ensuring it works also for non default template.")

    def test_theme_installed_on_current_website(self):
        """The theme in use is flagged for the current website only."""
        website = self.env.ref('base.default_website')
        other_website = self.env['website'].create({'name': 'Other Website'})
        theme = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website.theme_id = theme

        for context, installed in [
            ({'website_id': website.id}, True),
            ({'host_id': website.id}, True),
            ({'website_id': other_website.id}, False),
            ({}, False),
        ]:
            with self.subTest(context=context):
                self.assertEqual(
                    theme.with_context(**context).is_installed_on_current_website,
                    installed,
                )

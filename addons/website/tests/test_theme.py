from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTheme(common.TransactionCase):

    def test_theme_remove_working(self):
        """ This test ensure theme can be removed.
        Theme removal is also the first step during theme installation.
        """
        theme_common_module = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website = self.env['website'].get_current_website()
        website.theme_id = theme_common_module.id
        self.env['ir.module.module']._theme_remove(website)

    def test_02_disable_view(self):
        """This test ensure only one template header can be active at a time."""
        website_id = self.env['website'].browse(1)
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

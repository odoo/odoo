from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTheme(common.TransactionCase):

    def test_theme_remove_working(self):
        """ This test ensure theme can be removed.
        Theme removal is also the first step during theme installation.
        """
        theme_common_module = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        self.env.ref('base.default_website').theme_id = theme_common_module.id
        self.env['ir.module.module']._theme_remove(self.env.ref('base.default_website'))

    def test_theme_installed_on_current_website_via_host_id(self):
        """ The themes kanban reads this field over a backend route, for which
        `ir.http._match` moved `website_id` to `host_id`.
        """
        website = self.env.ref('base.default_website')
        theme = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website.theme_id = theme

        self.assertTrue(theme.with_context(host_id=website.id).is_installed_on_current_website)
        self.assertTrue(theme.with_context(website_id=website.id).is_installed_on_current_website)

    def test_theme_installed_on_current_website_not_shared(self):
        """ The field is context dependent, two websites must not share its value. """
        website = self.env.ref('base.default_website')
        other_website = self.env['website'].create({'name': 'Other Website'})
        theme = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website.theme_id = theme
        other_website.theme_id = False

        self.assertTrue(theme.with_context(host_id=website.id).is_installed_on_current_website)
        self.assertFalse(theme.with_context(host_id=other_website.id).is_installed_on_current_website)

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

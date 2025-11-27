# coding: utf-8
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

        key = 'website.template_header_magazine'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Only one template can be active at a time.")

        key = 'website.template_header_hamburger'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Ensuring it works also for non default template.")

    def test_theme_cleanup_preserves_cow_views(self):
        """Ensure _theme_cleanup does not delete user-modified COW views.

        COW views are created when users edit generic views
        from the website. These views have no theme_template_id
        (because theme_template_id has copy=False), but they should NOT be
        deleted as orphans because their generic parent still exists.
        """
        website = self.env['website'].get_current_website()
        View = self.env['ir.ui.view']

        generic = View.search([
            ('key', '=', 'website.footer_custom'),
            ('website_id', '=', False),
        ], limit=1)
        self.assertTrue(generic, "Need generic footer view for test")

        cow = generic.copy({'website_id': website.id, 'key': generic.key})
        cow_id = cow.id

        self.assertFalse(cow.theme_template_id,
            "COW view should not have theme_template_id (copy=False)")

        website_module = self.env['ir.module.module'].search([('name', '=', 'website')])
        website_module._theme_cleanup('ir.ui.view', website)

        self.assertTrue(View.browse(cow_id).exists(),
            "_theme_cleanup incorrectly deleted COW view. "
            "Views with existing generic parents should not be deleted.")

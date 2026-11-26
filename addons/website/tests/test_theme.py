from odoo.exceptions import AccessError
from odoo.tests import common, new_test_user, tagged


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


@tagged('-at_install', 'post_install')
class TestThemeApply(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].create({'name': 'Test Website'})
        cls.theme = cls.env['ir.module.module'].create({
            'name': 'test_theme',
            'state': 'installed',
            'category_id': cls.env.ref('base.module_category_theme').id,
        })
        cls.theme_view = cls.env['theme.ir.ui.view'].create({
            'name': 'Test Theme View',
            'key': 'test_theme.test_view',
            'arch': '<div>Hello</div>',
        })
        cls.env['ir.model.data'].create({
            'module': 'test_theme',
            'name': 'test_view',
            'model': 'theme.ir.ui.view',
            'res_id': cls.theme_view.id,
        })
        cls.designer = new_test_user(cls.env, 'test_theme_designer', groups='base.group_user,website.group_website_designer')

    def _get_view_copy(self):
        return self.env['ir.ui.view'].search([
            ('theme_template_id', '=', self.theme_view.id),
            ('website_id', '=', self.website.id),
        ])

    def test_choose_theme_access(self):
        """Only designers can choose a theme, and only a theme can be chosen."""
        restricted_editor = new_test_user(self.env, 'test_theme_restricted_editor', groups='base.group_user,website.group_website_restricted_editor')
        with self.assertRaises(AccessError):
            self.theme.with_user(restricted_editor).with_context(website_id=self.website.id).button_choose_theme()

        not_a_theme = self.env['ir.module.module'].create({'name': 'test_not_a_theme', 'state': 'uninstalled'})
        with self.assertRaises(ValueError):
            not_a_theme.with_user(self.designer).with_context(website_id=self.website.id).button_choose_theme()
        self.assertEqual(not_a_theme.state, 'uninstalled')

        self.theme.with_user(self.designer).with_context(website_id=self.website.id).button_choose_theme()
        self.assertEqual(self.website.theme_id, self.theme)
        self.assertTrue(self._get_view_copy())

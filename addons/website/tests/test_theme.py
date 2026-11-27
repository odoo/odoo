from odoo.exceptions import AccessError, MissingError
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
        ThemeUtils._enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Only one template can be active at a time.")

        key = 'website.template_header_hamburger'
        ThemeUtils._enable_view(key)
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
        cls.designer = new_test_user(cls.env, 'test_theme_designer', groups='base.group_user,website.group_website_designer')

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

    def test_uninstall_theme_removes_it_from_websites(self):
        self.env['theme.utils']._theme_apply(self.theme, self.website)

        self.theme.module_uninstall()

        self.assertFalse(self.website.theme_id)

    def test_theme_assets_only_apply_to_their_websites(self):
        self.env['ir.asset']._load_records([{
            'xml_id': 'test_theme.test_asset',
            'values': {
                'name': 'Test Theme Asset',
                'bundle': 'test_theme.assets',
                'path': 'website/static/src/scss/website.scss',
            },
        }])
        other_website = self.env['website'].create({'name': 'Other Website'})
        self.website.theme_id = self.theme

        def get_paths(website):
            return [path for path, *_ in self.env['ir.asset']._get_asset_paths('test_theme.assets', {'website_id': website.id})]

        self.assertEqual(get_paths(self.website), ['/website/static/src/scss/website.scss'])
        self.assertEqual(get_paths(other_website), [])

        self.website.theme_id = False
        self.assertEqual(get_paths(self.website), [])

    def test_theme_images_only_apply_to_their_websites(self):
        image = self.env['ir.attachment']._load_records([{
            'xml_id': 'test_theme.test_image',
            'values': {
                'name': 'Test Theme Image',
                'key': 'website.test_theme_image',
                'url': '/test_theme/static/src/img/test.webp',
            },
        }])
        self.assertRecordValues(image, [{
            'theme_id': self.theme.id,
            'type': 'url',
            'public': True,
            'res_model': 'ir.ui.view',
        }])
        other_website = self.env['website'].create({'name': 'Other Website'})
        self.website.theme_id = self.theme

        IrBinary = self.env['ir.binary']
        self.assertEqual(IrBinary.with_context(website_id=self.website.id)._find_record(xmlid='website.test_theme_image'), image)
        with self.assertRaises(MissingError):
            IrBinary.with_context(website_id=other_website.id)._find_record(xmlid='website.test_theme_image')

    def test_theme_views_only_apply_to_their_websites(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'Test Base View',
            'type': 'qweb',
            'key': 'website.test_theme_base_view',
            'arch': '<div>Base</div>',
        })
        theme_view = self.env['ir.ui.view']._load_records([{
            'xml_id': 'test_theme.test_view',
            'values': {
                'name': 'Test Theme View',
                'type': 'qweb',
                'key': 'test_theme.test_view',
                'inherit_id': base_view.id,
                'arch': '<div position="inside">From the theme</div>',
            },
        }])
        self.assertEqual(theme_view.theme_id, self.theme)
        other_website = self.env['website'].create({'name': 'Other Website'})
        self.website.theme_id = self.theme

        def render(website):
            return str(self.env['ir.qweb'].with_context(website_id=website.id)._render(base_view.key))

        self.assertIn('From the theme', render(self.website))
        self.assertNotIn('From the theme', render(other_website))

        # Edits made on a website are kept when it stops using the theme, and
        # come back if it uses it again
        theme_view.with_context(website_id=self.website.id).write({'arch': '<div position="inside">Edited</div>'})
        self.assertIn('Edited', render(self.website))
        self.website.theme_id = False
        self.assertNotIn('Edited', render(self.website))
        self.website.theme_id = self.theme
        self.assertIn('Edited', render(self.website))

    def test_theme_views_follow_edited_views_on_theme_switch(self):
        other_theme = self.env['ir.module.module'].create({
            'name': 'test_other_theme',
            'state': 'installed',
            'category_id': self.env.ref('base.module_category_theme').id,
        })
        base_view = self.env['ir.ui.view'].create({
            'name': 'Test Base View',
            'type': 'qweb',
            'key': 'website.test_theme_base_view',
            'arch': '<div>Base</div>',
        })
        self.env['ir.ui.view']._load_records([{
            'xml_id': 'test_other_theme.test_view',
            'values': {
                'name': 'Test Other Theme View',
                'type': 'qweb',
                'key': 'test_other_theme.test_view',
                'inherit_id': base_view.id,
                'arch': '<div position="inside">From the other theme</div>',
            },
        }])
        self.env['theme.utils']._theme_apply(self.theme, self.website)

        # Editing a view does not copy the views of a theme the website does not use
        base_view.with_context(website_id=self.website.id).write({'arch': '<div>Edited</div>'})
        self.assertFalse(self.env['ir.ui.view'].search([
            ('key', '=', 'test_other_theme.test_view'),
            ('website_id', '=', self.website.id),
        ]))

        # They are attached to the edited view once the website uses that theme
        self.env['theme.utils']._theme_apply(other_theme, self.website)
        html = str(self.env['ir.qweb'].with_context(website_id=self.website.id)._render(base_view.key))
        self.assertIn('Edited', html)
        self.assertIn('From the other theme', html)

    def test_installed_theme_views_follow_edited_views_of_its_websites(self):
        base_view = self.env['ir.ui.view'].create({
            'name': 'Test Base View',
            'type': 'qweb',
            'key': 'website.test_theme_base_view',
            'arch': '<div>Base</div>',
        })
        other_website = self.env['website'].create({'name': 'Other Website'})
        self.website.theme_id = self.theme
        for website in self.website + other_website:
            base_view.with_context(website_id=website.id).write({'arch': '<div>Edited</div>'})

        # A theme installed after the edits only reaches the websites using it
        self.env['ir.ui.view']._load_records([{
            'xml_id': 'test_theme.test_view',
            'values': {
                'name': 'Test Theme View',
                'type': 'qweb',
                'key': 'test_theme.test_view',
                'inherit_id': base_view.id,
                'arch': '<div position="inside">From the theme</div>',
            },
        }])
        self.env['ir.ui.view']._create_all_specific_views(['test_theme'])
        copies = self.env['ir.ui.view'].search([('key', '=', 'test_theme.test_view'), ('website_id', '!=', False)])
        self.assertEqual(copies.website_id, self.website)

from odoo.tests import HttpCase, common, tagged


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
class TestThemePreviewParity(HttpCase):
    """Without any change, the Theme tab colors preview equals the compiled
    colors (see `website_theme_preview_parity`)."""

    def _check_parity(self, palette):
        assets = self.env['website.assets'].with_context(website_id=self.env.ref('base.default_website').id)
        assets.make_scss_customization('/website/static/src/scss/options/user_values.scss', {
            'color-palettes-name': f"'{palette}'",
            'o-cc3-bg-gradient': "'linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)'",
        })
        # Some set preset and area colors, over the palette's.
        assets.make_scss_customization('/website/static/src/scss/options/colors/user_color_palette.scss', {
            'o-cc2-headings': "'o-color-1'",
            'o-cc2-h3': '#AA3300',
            'o-cc4-link': '#1E7B34',
            'o-cc5-btn-primary': '#123456',
            'menu': '2',
            'footer-custom': '#335577',
        })
        self.start_tour(self.env['website'].get_client_action_url('/', True), 'website_theme_preview_parity', login='admin')

    def test_light_palette(self):
        self._check_parity('default-light-1')

    def test_dark_palette(self):
        self._check_parity('default-dark-1')

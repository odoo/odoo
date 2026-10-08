# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo.tests
from odoo.addons.website.controllers.main import Website as WebsiteController
from odoo.addons.website.models.website import Website as WebsiteModel
from odoo.tests.common import new_test_user

class TestConfiguratorCommon(odoo.tests.HttpCase):

    def _theme_upgrade_upstream(self):
        # patch to prevent module install/upgrade during tests, but still generate the snippet templates the configurator needs.
        self._generate_primary_snippet_templates()

    def setUp(self):
        super().setUp()

        def iap_jsonrpc_mocked_configurator(*args, **kwargs):
            endpoint = args[0]
            params = kwargs.get('params', {})
            language = params.get('lang', 'en_US')
            if endpoint.endswith('/api/website/1/configurator/industries'):
                if language in ('fr_FR', 'pa_GB'):
                    return {"industries": [
                        {"id": 1, "label": "abbey in fr"},
                        {"id": 2, "label": "aboriginal and torres strait islander organisation in fr"},
                        {"id": 3, "label": "aboriginal art gallery in fr"},
                        {"id": 4, "label": "abortion clinic in fr"},
                        {"id": 5, "label": "abrasives supplier in fr"},
                        {"id": 6, "label": "abundant life church in fr"}]}
                else:
                    return {"industries": [
                        {"id": 1, "label": "abbey"},
                        {"id": 2, "label": "aboriginal and torres strait islander organisation"},
                        {"id": 3, "label": "aboriginal art gallery"},
                        {"id": 4, "label": "abortion clinic"},
                        {"id": 5, "label": "abrasives supplier"},
                        {"id": 6, "label": "abundant life church"}]}
            elif 'api/olg/1/chat' in endpoint:
                return {
                    'status': 'success',
                    'content': '''
                    {
                    "categories": [
                        {
                        "name": "New Arrivals",
                        "description": "Fresh styles just dropped—grab them before they’re gone!"
                        },
                        {
                        "name": "Best Sellers",
                        "description": "Shop the crowd favorites everyone’s raving about."
                        },
                        {
                        "name": "Limited Editions",
                        "description": "Exclusive finds you won’t see again. Act fast!"
                        },
                        {
                        "name": "Eco-Friendly Picks",
                        "description": "Sustainable choices that look good and feel better."
                        },
                        {
                        "name": "Gifts & Bundles",
                        "description": "Perfectly curated sets for every occasion."
                        },
                        {
                        "name": "Under $50",
                        "description": "Amazing deals that won’t break the bank."
                        },
                        {
                        "name": "Seasonal Favorites",
                        "description": "Style your season with trending must-haves."
                        },
                        {
                        "name": "Final Sale",
                        "description": "Last chance to score these unbeatable deals!"
                        }
                    ]
                    }
                '''
                }
            elif '/api/website/2/configurator/recommended_themes' in endpoint:
                return []
            elif '/api/website/2/configurator/custom_resources/' in endpoint:
                return {'images': {}}
            elif '/api/olg/1/generate_placeholder' in endpoint:
                return {"a non existing placeholder": "😠", 'Catchy Headline': 'Welcome to XXXX - Your Super test'}

        iap_patch = patch('odoo.addons.iap.tools.iap_tools.iap_jsonrpc', iap_jsonrpc_mocked_configurator)
        self.startPatcher(iap_patch)

        patcher = patch(
            'odoo.addons.website.models.ir_module_module.IrModuleModule._theme_upgrade_upstream',
            new=TestConfiguratorCommon._theme_upgrade_upstream,
        )
        self.startPatcher(patcher)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(TestConfiguratorCommon):

    def test_ai_recommend_themes(self):
        def iap_jsonrpc_mocked_olg(*args, **kwargs):
            return {
                'status': 'success',
                'content': '["theme_clean", "theme_cobalt", "theme_unknown"]',
            }

        with patch('odoo.addons.iap.tools.iap_tools.iap_jsonrpc', iap_jsonrpc_mocked_olg):
            themes = self.env['website']._ai_recommend_themes(
                {
                    'theme_clean': 'Clean theme',
                    'theme_cobalt': 'Cobalt theme',
                },
                'restaurant',
                'business',
                'premium',
                6,
            )

        self.assertEqual(themes, ['theme_clean', 'theme_cobalt'])

    def test_ai_recommend_themes_wrong_answer(self):
        def iap_jsonrpc_mocked_olg(*args, **kwargs):
            return {
                'status': 'success',
                'content': '[{"name": "New Arrivals", "description": "Fresh styles"}]',
            }

        with patch('odoo.addons.iap.tools.iap_tools.iap_jsonrpc', iap_jsonrpc_mocked_olg):
            themes = self.env['website']._ai_recommend_themes(
                {
                    'theme_clean': 'Clean theme',
                    'theme_cobalt': 'Cobalt theme',
                },
                'restaurant',
                'business',
                'premium',
                6,
            )

        self.assertEqual(themes, [])

    def test_configurator_params_step(self):
        self.start_tour('/website/configurator/2', 'configurator_params_step', login='admin')

    def test_configurator_page_creation(self):
        website = self.env['website'].create({
            'name': "New website",
        })
        self.start_tour('/website/force/%s?path=%%2Fwebsite%%2Fconfigurator' % website.id, 'configurator_page_creation', login='admin')

@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfiguratorTranslation(TestConfiguratorCommon):

    def test_01_configurator_translation(self):
        parseltongue = self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [parseltongue.id])],
        }).lang_install()
        self.env.ref('base.user_admin').write({'lang': parseltongue.code})
        website_fr = self.env['website'].create({
            'name': "New website",
        })
        # disable configurator todo to ensure this test goes through
        active_todo = self.env['ir.actions.todo'].search([('state', '=', 'open')], limit=1)
        active_todo.update({'state': 'done'})
        self.start_tour(
            '/website/force/%s?path=%%2Fwebsite%%2Fconfigurator' % website_fr.id,
            'configurator_translation',
            login='admin',
            timeout=120,
        )


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfiguratorPreview(odoo.tests.HttpCase):
    """The preview route renders a static theme file with request parameters."""

    PREVIEW_HTML = '<html><head><title>preview marker</title></head><body></body></html>'
    LISTED_PREVIEW_URL = '/ecommerce_previews/cards.html'

    def setUp(self):
        super().setUp()

        def preview_url_mocked(website, theme_name):
            # No module in the test addons path ships a preview file.
            if theme_name == 'theme_default':
                return '/theme_default/static/description/preview.html'
            return None

        self.patch(WebsiteModel, '_get_configurator_theme_preview_url', preview_url_mocked)
        self.patch(WebsiteController, '_load_configurator_preview_html', lambda controller, url: self.PREVIEW_HTML)

    def _preview(self, **params):
        params.setdefault('theme_name', 'theme_default')
        query = '&'.join(f'{key}={value}' for key, value in params.items() if value is not None)
        return self.url_open(f'/website/configurator/preview?{query}')

    def test_preview_requires_a_designer(self):
        for login, groups, status in [
            ('preview_portal', 'base.group_portal', 404),
            ('preview_employee', 'base.group_user', 404),
            ('preview_designer', 'website.group_website_designer', 200),
        ]:
            new_test_user(self.env, login=login, groups=groups, password=login)
            self.authenticate(login, login)
            self.assertEqual(self._preview().status_code, status, f'{login} on the preview route')

    def test_preview_rejects_an_invalid_theme_name(self):
        self.authenticate('admin', 'admin')
        for theme_name in (
            'theme_default/../website',     # traversal on a valid theme
            'theme_unknown',                # no such module
            'website',                      # a module, but not a theme
        ):
            self.assertEqual(self._preview(theme_name=theme_name).status_code, 404, repr(theme_name))

    def test_preview_only_keeps_hex_colors(self):
        self.authenticate('admin', 'admin')
        kept = self._preview(color1='%23714B67')
        self.assertIn('--o-color-1: #714B67;', kept.text)

        dropped = self._preview(color1='red;--x:y')
        self.assertNotIn('--o-color-1', dropped.text)
        self.assertNotIn('red;--x:y', dropped.text)

    def test_preview_only_renders_a_listed_preview_url(self):
        # website doesn't depend on website_sale: fake its allow-listing of
        # the eCommerce preview pages instead of relying on the real module.
        self.patch(
            WebsiteModel, '_get_configurator_preview_urls',
            lambda website: {self.LISTED_PREVIEW_URL},
        )
        self.authenticate('admin', 'admin')

        self.assertEqual(self._preview(preview_url=self.LISTED_PREVIEW_URL).status_code, 200)
        for preview_url in (
            '/website/static/description/preview.html',  # not in the allow-list
            '/ecommerce_previews/../x.html',  # traversal attempt
        ):
            self.assertEqual(self._preview(preview_url=preview_url).status_code, 404, repr(preview_url))

    def test_preview_substitutes_catalog_texts(self):
        catalog_html = (
            '<html><head><title>preview marker</title></head><body>'
            '<span industry_text_key="website.prod_sq_1.product_name">Desk</span>'
            '<span industry_text_key="website.prod_sq_1.price">10.00</span>'
            '<span industry_text_key="website.prod_sq_2.product_name">Chair</span>'
            '</body></html>'
        )
        self.patch(WebsiteController, '_load_configurator_preview_html', lambda controller, url: catalog_html)
        self.patch(
            WebsiteController, '_get_configurator_preview_resources',
            lambda controller, theme_name, industry_id: {
                'images': {},
                'catalog': {'website.prod_sq_1': {'product_name': '<b>Pizza</b>', 'price': 12.5}},
            },
        )
        self.authenticate('admin', 'admin')

        text = self._preview().text
        self.assertIn(
            '<span industry_text_key="website.prod_sq_1.product_name">&lt;b&gt;Pizza&lt;/b&gt;</span>',
            text,
        )
        self.assertIn('<span industry_text_key="website.prod_sq_1.price">12.50</span>', text)
        self.assertIn('<span industry_text_key="website.prod_sq_2.product_name">Chair</span>', text)

    def test_preview_resources_receive_a_theme_name_only_without_a_preview_url(self):
        received_theme_names = []

        def preview_resources_mocked(controller, theme_name, industry_id):
            received_theme_names.append(theme_name)
            return {}

        self.patch(WebsiteController, '_get_configurator_preview_resources', preview_resources_mocked)
        self.patch(
            WebsiteModel, '_get_configurator_preview_urls',
            lambda website: {self.LISTED_PREVIEW_URL},
        )
        self.authenticate('admin', 'admin')

        self._preview(preview_url=self.LISTED_PREVIEW_URL, industry_id=1)
        self._preview(industry_id=1)

        self.assertEqual(received_theme_names, ['', 'theme_default'])

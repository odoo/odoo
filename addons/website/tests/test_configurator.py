# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo.tests

class TestConfiguratorCommon(odoo.tests.HttpCase):

    def _theme_upgrade_upstream(self):
        # patch to prevent module install/upgrade during tests
        pass

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

        patcher = patch('odoo.addons.website.models.ir_module_module.IrModuleModule._theme_upgrade_upstream', wraps=self._theme_upgrade_upstream)
        self.startPatcher(patcher)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(TestConfiguratorCommon):

    def test_configurator_params_step(self):
        self.start_tour('/website/configurator/3', 'configurator_params_step', login='admin')

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
        feature = self.env['website.configurator.feature'].search([('name', '=', 'Privacy Policy')])
        feature.with_context(lang=parseltongue.code).write({'name': 'Parseltongue_privacy'})
        self.env.ref('base.user_admin').write({'lang': parseltongue.code})
        website_fr = self.env['website'].create({
            'name': "New website",
        })
        # disable configurator todo to ensure this test goes through
        active_todo = self.env['ir.actions.todo'].search([('state', '=', 'open')], limit=1)
        active_todo.update({'state': 'done'})
        self.start_tour('/website/force/%s?path=%%2Fwebsite%%2Fconfigurator' % website_fr.id, 'configurator_translation', login='admin')

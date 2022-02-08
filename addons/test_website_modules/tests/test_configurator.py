# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo.tests
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc_mocked


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(odoo.tests.HttpCase):

    def _theme_upgrade_upstream(self):
        # patch to prevent module install/upgrade during tests
        pass

    def setUp(self):
        super().setUp()

        def iap_jsonrpc_mocked_configurator(*args, **kwargs):
            endpoint = args[0]
            if endpoint.endswith('/api/website/1/configurator/industries'):
                return {"industries": [
                    {"id": 1, "label": "abbey"},
                    {"id": 2, "label": "aboriginal and torres strait islander organisation"},
                    {"id": 3, "label": "aboriginal art gallery"},
                    {"id": 4, "label": "abortion clinic"},
                    {"id": 5, "label": "abrasives supplier"},
                    {"id": 6, "label": "abundant life church"}]}
            elif '/api/website/2/configurator/recommended_themes' in endpoint:
                return []
            elif '/api/website/2/configurator/custom_resources/' in endpoint:
                return {'images': {}}

            iap_jsonrpc_mocked()

        iap_patch = patch('odoo.addons.iap.tools.iap_tools.iap_jsonrpc', iap_jsonrpc_mocked_configurator)
        iap_patch.start()
        self.addCleanup(iap_patch.stop)

        patcher = patch('odoo.addons.website.models.ir_module_module.IrModuleModule._theme_upgrade_upstream', wraps=self._theme_upgrade_upstream)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_01_configurator_flow(self):
        self.start_tour('/web#action=website.action_website_configuration', 'configurator_flow', login="admin")

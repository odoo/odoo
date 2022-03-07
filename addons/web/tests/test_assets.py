# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

import odoo
import odoo.tests

from odoo.modules.module import read_manifest
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


class TestAssetsGenerateTimeCommon(odoo.tests.TransactionCase):

    def generate_bundles(self):
        bundles = set()
        installed_module_names = self.env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
        for addon_path in odoo.addons.__path__:
            for addon in installed_module_names:
                manifest = read_manifest(addon_path, addon) or {}
                assets = manifest.get('assets')
                if assets:
                    bundles |= set(assets.keys())

        for bundle in bundles:
            with mute_logger('odoo.addons.base.models.assetsbundle'):
                for assets_type in 'css', 'js':
                    try:
                        start_t = time.time()
                        css = assets_type == 'css'
                        js = assets_type == 'js'
                        self.env['ir.qweb']._generate_asset_nodes(bundle, css=css, js=js)
                        yield (f'{bundle}.{assets_type}', time.time() - start_t)
                    except ValueError:
                        _logger.info('Error detected while generating bundle %r %s', bundle, assets_type)


@odoo.tests.tagged('post_install', '-at_install')
class TestLogsAssetsGenerateTime(TestAssetsGenerateTimeCommon):

    def test_logs_assets_generate_time(self):
        """
        The purpose of this test is to monitor the time of assets bundle generation.
        This is not meant to test the generation failure, hence the try/except and the mute logger.
        For example, 'web.assets_qweb' is contains only static xml.
        """
        for bundle, duration in self.generate_bundles():
            _logger.info('Bundle %r generated in %.2fs', bundle, duration)


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'bundle_generation')
class TestAssetsGenerateTime(TestAssetsGenerateTimeCommon):
    """
    This test is meant to be run nightly to ensure bundle generation does not exceed
    a low threshold
    """

    def test_assets_generate_time(self):
        thresholds = {
            'web.qunit_suite_tests.js': 3.6,
            'project.webclient.js': 2.5,
            'point_of_sale.pos_assets_backend.js': 2.5,
            'web.assets_backend.js': 2.5,
        }
        for bundle, duration in self.generate_bundles():
            threshold = thresholds.get(bundle, 2)
            self.assertLess(duration, threshold, "Bundle %r took more than %s sec" % (bundle, threshold))

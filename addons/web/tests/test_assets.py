# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

import odoo
import odoo.tests

from odoo.tests.common import HttpCase
from odoo.modules.module import get_manifest
from odoo.tools import mute_logger

from unittest.mock import patch

_logger = logging.getLogger(__name__)


class TestAssetsGenerateTimeCommon(odoo.tests.TransactionCase):

    def generate_bundles(self, unlink=True):
        if unlink:
            self.env['ir.attachment'].search([('url', '=like', '/web/assets/%')]).unlink()  # delete existing attachement
        installed_module_names = self.env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
        bundles = {
            key
            for module in installed_module_names
            for key in get_manifest(module).get('assets', [])
        }

        for bundle_name in bundles:
            with mute_logger('odoo.addons.base.models.assetsbundle'):
                for assets_type in 'css', 'js':
                    try:
                        start_t = time.time()
                        css = assets_type == 'css'
                        js = assets_type == 'js'
                        bundle = self.env['ir.qweb']._get_asset_bundle(bundle_name, css=css, js=js)
                        if assets_type == 'css' and bundle.stylesheets:
                            bundle.css()
                        if assets_type == 'js' and bundle.javascripts:
                            bundle.js()
                        yield (f'{bundle_name}.{assets_type}', time.time() - start_t)
                    except ValueError:
                        _logger.info('Error detected while generating bundle %r %s', bundle_name, assets_type)


@odoo.tests.tagged('post_install', '-at_install', 'assets_bundle')
class TestLogsAssetsGenerateTime(TestAssetsGenerateTimeCommon):

    def test_logs_assets_generate_time(self):
        """
        The purpose of this test is to monitor the time of assets bundle generation.
        This is not meant to test the generation failure, hence the try/except and the mute logger.
        """
        for bundle, duration in list(self.generate_bundles()):
            _logger.info('Bundle %r generated in %.2fs', bundle, duration)

    def test_logs_assets_check_time(self):
        """
        The purpose of this test is to monitor the time of assets bundle generation.
        This is not meant to test the generation failure, hence the try/except and the mute logger.
        """
        start = time.time()
        for bundle, duration in self.generate_bundles(False):
            _logger.info('Bundle %r checked in %.2fs', bundle, duration)
        duration = time.time() - start
        _logger.info('All bundle checked in %.2fs', duration)


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'test_assets')
class TestPregenerateTime(HttpCase):

    def test_logs_pregenerate_time(self):
        self.env['ir.qweb']._pregenerate_assets_bundles()
        start = time.time()
        self.env.registry.clear_cache()
        self.env.cache.invalidate()
        with self.profile(collectors=['sql', odoo.tools.profiler.PeriodicCollector(interval=0.01)], disable_gc=True):
            self.env['ir.qweb']._pregenerate_assets_bundles()
        duration = time.time() - start
        _logger.info('All bundle checked in %.2fs', duration)

@odoo.tests.tagged('post_install', '-at_install', '-standard', 'assets_bundle')
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

@odoo.tests.tagged('post_install', '-at_install')
class TestLoad(HttpCase):
    def test_assets_already_exists(self):
        self.authenticate('admin', 'admin')
        # TODO xdo adapt this test. url open won't generate attachment anymore even if not pregenerated
        _save_attachment = odoo.addons.base.models.assetsbundle.AssetsBundle.save_attachment

        def save_attachment(bundle, extension, content):
            attachment = _save_attachment(bundle, extension, content)
            message = f"Trying to save an attachement for {bundle.name} when it should already exist: {attachment.url}"
            _logger.error(message)
            return attachment

        with patch('odoo.addons.base.models.assetsbundle.AssetsBundle.save_attachment', save_attachment):
            self.url_open('/web').raise_for_status()
            self.url_open('/').raise_for_status()

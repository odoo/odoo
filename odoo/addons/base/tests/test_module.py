# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os.path
import tempfile
from os.path import join as opj
from unittest.mock import patch

import odoo.addons
from odoo.modules.module import load_manifest
from odoo.modules.module import get_manifest
from odoo.release import major_version
from odoo.tests.common import BaseCase


class TestModuleManifest(BaseCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix='odoo-test-addons-')
        cls.addClassCleanup(cls._tmp_dir.cleanup)
        cls.addons_path = cls._tmp_dir.name

        patcher = patch.object(odoo.addons, '__path__', [cls.addons_path])
        cls.startClassPatcher(patcher)

    def setUp(self):
        self.module_root = tempfile.mkdtemp(prefix='odoo-test-module-', dir=self.addons_path)
        self.module_name = os.path.basename(self.module_root)

    def test_default_manifest(self):
        with open(opj(self.module_root, '__manifest__.py'), 'w') as file:
            file.write(str({'name': f'Temp {self.module_name}', 'license': 'MIT'}))

        with self.assertNoLogs('odoo.modules.module', 'WARNING'):
            manifest = load_manifest(self.module_name)

        self.maxDiff = None
        self.assertDictEqual(manifest, {
            'addons_path': self.addons_path,
            'application': False,
            'assets': {},
            'author': 'Odoo S.A.',
            'auto_install': False,
            'bootstrap': False,
            'category': 'Uncategorized',
            'data': [],
            'demo': [],
            'demo_xml': [],
            'depends': [],
            'description': '',
            'external_dependencies': [],
            'icon': '/base/static/description/icon.png',
            'init_xml': [],
            'installable': True,
            'images': [],
            'images_preview_theme': {},
            'license': 'MIT',
            'live_test_url': '',
            'name': f'Temp {self.module_name}',
            'post_init_hook': '',
            'post_load': None,
            'pre_init_hook': '',
            'sequence': 100,
            'snippet_lists': {},
            'summary': '',
            'test': [],
            'update_xml': [],
            'uninstall_hook': '',
            'version': f'{major_version}.1.0',
            'web': False,
            'website': '',
        })

    def test_change_manifest(self):
        module_name = 'base'
        new_manifest = get_manifest(module_name)
        orig_auto_install = new_manifest['auto_install']
        new_manifest['auto_install'] = not orig_auto_install
        self.assertNotEqual(new_manifest, get_manifest(module_name))
        self.assertEqual(orig_auto_install, get_manifest(module_name)['auto_install'])

    def test_missing_manifest(self):
        with self.assertLogs('odoo.modules.module', 'DEBUG') as capture:
            manifest = load_manifest(self.module_name)
        self.assertEqual(manifest, {})
        self.assertIn("no manifest file found", capture.output[0])

    def test_missing_license(self):
        with open(opj(self.module_root, '__manifest__.py'), 'w') as file:
            file.write(str({'name': f'Temp {self.module_name}'}))
        with self.assertLogs('odoo.modules.module', 'WARNING') as capture:
            manifest = load_manifest(self.module_name)
        self.assertEqual(manifest['license'], 'LGPL-3')
        self.assertIn("Missing `license` key", capture.output[0])

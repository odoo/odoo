# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os.path
import tempfile
import time
from os.path import join as opj
from unittest.mock import patch
from logging import getLogger

import odoo.addons
from odoo.modules.module import load_manifest
from odoo.modules.module import get_manifest
from odoo.release import major_version
from odoo.tests.common import BaseCase, TransactionCase, warmup

_logger = getLogger(__name__)


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
            'configurator_snippets': {},
            'countries': [],
            'data': [],
            'demo': [],
            'demo_xml': [],
            'depends': [],
            'description': '',
            'external_dependencies': {},
            'icon': '/base/static/description/icon.png',
            'init_xml': [],
            'installable': True,
            'images': [],
            'images_preview_theme': {},
            'license': 'MIT',
            'live_test_url': '',
            'name': f'Temp {self.module_name}',
            'new_page_templates': {},
            'post_init_hook': '',
            'post_load': '',
            'pre_init_hook': '',
            'sequence': 100,
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

class TestIrModule(TransactionCase):

    def downstream_dependencies_legacy(self, modules, known_deps=None,
                                exclude_states=('uninstalled', 'uninstallable', 'to remove')):
        """ Return the modules that directly or indirectly depend on the modules
        in `self`, and that satisfy the `exclude_states` filter.
        """
        if not modules:
            return modules
        modules.flush_model(['name', 'state'])
        modules.env['ir.module.module.dependency'].flush_model(['module_id', 'name'])
        known_deps = known_deps or modules.browse()
        query = """ SELECT DISTINCT m.id
                        FROM ir_module_module_dependency d
                        JOIN ir_module_module m ON (d.module_id=m.id)
                        WHERE
                            d.name IN (SELECT name from ir_module_module where id in %s) AND
                            m.state NOT IN %s AND
                            m.id NOT IN %s """
        modules._cr.execute(query, (tuple(modules.ids), tuple(exclude_states), tuple(known_deps.ids or modules.ids)))
        new_deps = modules.browse([row[0] for row in modules._cr.fetchall()])
        missing_mods = new_deps - known_deps
        known_deps |= new_deps
        if missing_mods:
            known_deps |= self.downstream_dependencies_legacy(missing_mods, known_deps, exclude_states)
        return known_deps

    def upstream_dependencies_legacy(self, modules, known_deps=None,
                              exclude_states=('installed', 'uninstallable', 'to remove')):
        """ Return the dependency tree of modules of the modules in `self`, and
        that satisfy the `exclude_states` filter.
        """
        if not modules:
            return modules
        modules.flush_model(['name', 'state'])
        modules.env['ir.module.module.dependency'].flush_model(['module_id', 'name'])
        known_deps = known_deps or modules.browse()
        query = """ SELECT DISTINCT m.id
                    FROM ir_module_module_dependency d
                    JOIN ir_module_module m ON (d.module_id=m.id)
                    WHERE
                        m.name IN (SELECT name from ir_module_module_dependency where module_id in %s) AND
                        m.state NOT IN %s AND
                        m.id NOT IN %s """
        modules._cr.execute(query, (tuple(modules.ids), tuple(exclude_states), tuple(known_deps.ids or modules.ids)))
        new_deps = modules.browse([row[0] for row in modules._cr.fetchall()])
        missing_mods = new_deps - known_deps
        known_deps |= new_deps
        if missing_mods:
            known_deps |= self.upstream_dependencies_legacy(missing_mods, known_deps, exclude_states)
        return known_deps

    @warmup
    def test_downstream_dependencies(self):
        module_base = self.env['ir.module.module'].search([('name', '=', 'base')])
        t0 = time.time()
        dependents_legacy = self.downstream_dependencies_legacy(module_base, exclude_states=('dummy',))
        t1 = time.time()

        t2 = time.time()
        dependents = module_base.downstream_dependencies(exclude_states=('dummy',))
        t3 = time.time()

        if self.warm:
            self.assertEqual(dependents_legacy, dependents)
            _logger.info('legacy upstream_dependencies time %.6fs', t1 - t0)
            _logger.info('current upstream_dependencies time %.6fs', t3 - t2)

    @warmup
    def test_upstream_dependencies(self):
        module_industry_fsm_stock = self.env['ir.module.module'].search([('name', '=', 'industry_fsm_stock')])
        if not module_industry_fsm_stock:  # the module with the deepest depth 16
            return
        module_base = self.env['ir.module.module'].search([('name', '=', 'base')])
        t0 = time.time()
        depends_legacy = self.upstream_dependencies_legacy(module_industry_fsm_stock, exclude_states=('dummy',))
        t1 = time.time()

        t2 = time.time()
        depends = module_industry_fsm_stock.upstream_dependencies(exclude_states=('dummy',))
        t3 = time.time()

        if self.warm:
            # the upstream_dependencies_legacy won't return the last layer of depends
            # it should be treated as a bug since it against its definition
            # but it is a safe bug, since the last layer of depends is always 'base' which should always be installed
            self.assertEqual(depends_legacy | module_base, depends)
            _logger.info('legacy upstream_dependencies time %.6fs', t1 - t0)
            _logger.info('current upstream_dependencies time %.6fs', t3 - t2)

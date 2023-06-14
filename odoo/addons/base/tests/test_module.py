# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os.path
import tempfile
from os.path import join as opj
from unittest.mock import patch

import odoo.addons
from odoo.modules.module import load_manifest
from odoo.release import major_version
from odoo.tests.common import BaseCase, TransactionCase, tagged


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


@tagged('-at_install', 'post_install')
class TestModuleDependencies(TransactionCase):
    def test_main_modules(self):
        """Ensure that the one app free doesn't change over time, unless explicitely decided."""
        excluded_apps = (
            self.env.ref('base.module_calendar')
            + self.env.ref('base.module_contacts')
            + self.env.ref('base.module_mail')
            + self.env.ref('base.module_mass_mailing')
        )
        allowed = {
            'account_accountant': ['account'],
            'account_consolidation': ['account', 'account_accountant'],
            'approvals': ['hr'],
            'delivery_bpost': ['sale_management', 'account', 'stock'],
            'delivery_dhl': ['sale_management', 'account', 'stock'],
            'delivery_easypost': ['sale_management', 'account', 'stock'],
            'delivery_fedex': ['sale_management', 'account', 'stock'],
            'delivery_sendcloud': ['sale_management', 'account', 'stock'],
            'delivery_ups': ['sale_management', 'account', 'stock'],
            'delivery_usps': ['sale_management', 'account', 'stock'],
            'hr_appraisal': ['hr'],
            'hr_attendance': ['hr'],
            'hr_contract': ['hr'],
            'hr_expense': ['account', 'hr'],
            'hr_holidays': ['hr'],
            'hr_payroll': ['hr', 'hr_contract'],
            'hr_recruitment': ['hr'],
            'hr_referral': ['website', 'hr_recruitment', 'hr', 'website_hr_recruitment'],
            'hr_skills': ['hr'],
            'industry_fsm': ['project', 'timesheet_grid', 'hr'],
            'mrp': ['stock'],
            'mrp_plm': ['stock', 'mrp'],
            'planning': ['hr'],
            'point_of_sale': ['account', 'stock'],
            'project_todo': ['project'],
            'purchase': ['account'],
            'quality_control': ['stock'],
            'repair': ['sale_management', 'account', 'stock'],
            'sale_amazon': ['sale_management', 'account', 'stock'],
            'sale_ebay': ['sale_management', 'account', 'stock'],
            'sale_management': ['account'],
            'sale_renting': ['account'],
            'sale_subscription': ['sale_management', 'account', 'account_accountant'],
            'stock_barcode': ['stock'],
            'timesheet_grid': ['project', 'hr'],
            'website_event': ['website'],
            'website_hr_recruitment': ['website', 'hr_recruitment', 'hr'],
            'website_sale': ['account', 'website'],
            'website_slides': ['website'],
        }
        main_apps = self.env['ir.module.module'].search([('application', '=', True)])
        for app in main_apps:
            dependencies = app.upstream_dependencies(exclude_states={'uninstallable'})
            main_dependencies = main_apps & dependencies - excluded_apps
            if main_dependencies:
                self.assertEqual(main_dependencies.mapped('name'), allowed.get(app.name, []), f"Dependency change for {app.name}")

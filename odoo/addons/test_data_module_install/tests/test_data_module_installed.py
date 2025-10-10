# -*- coding: utf-8 -*-
from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestDataModuleInstalled(common.TransactionCase):
    """ Test that the fake data module `test_data_module` is correctly installed.
    The use case of this test is that odoo supports installation of data modules only without `__init__.py`.
    """

    def test_data_module_installed(self):

        data_module = self.env['ir.module.module'].search([('name', '=', 'test_data_module')])
        self.assertEqual(data_module.state, 'installed')

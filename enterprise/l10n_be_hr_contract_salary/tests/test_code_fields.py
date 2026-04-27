# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCodeField(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_get_available_fields(self):
        '''
            tests if no unneeded duplicate values are present
            in hr.contract.salary.resume code field 'Selection'
        '''

        salary_resume = self.env['hr.contract.salary.resume'].search([('id', '=', 0)])
        code_selection = salary_resume._get_available_fields()
        unique_entries_tuple = set(code_selection)
        self.assertEqual(len(code_selection), len(unique_entries_tuple))

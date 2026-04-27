# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPayrollDependencies(TransactionCase):

    def test_l10n_xx_hr_payroll_no_account(self):
        for module in self.env['ir.module.module'].search([('name', '=like', 'l10n____hr_payroll')]):
            dependencies = module.upstream_dependencies(exclude_states=('uninstallable')).mapped('name')
            self.assertTrue('hr_payroll' in dependencies, "The payroll localization %s should depend on payroll" % module.name)
            self.assertFalse('account' in dependencies, "The payroll localization %s shouldn't depend on accounting" % module.name)

        for module in self.env['ir.module.module'].search([('name', '=like', 'l10n____hr_payroll_account')]):
            dependencies = module.upstream_dependencies(exclude_states=('uninstallable')).mapped('name')
            self.assertTrue(module.name[:18] in dependencies, "The payroll localization %s should depend on %s" % (module.name, module.name[:18]))
            self.assertTrue('account' in dependencies, "The payroll localization %s shouldn't depend on accounting" % module.name)

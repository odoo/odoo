# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestHrEmployeeRights(TestHrCommon):

    @classmethod
    def _get_payroll_l10n_modules(cls):
        return cls.env['ir.module.module'].search([
            ('name', '=like', 'l10n\\_%\\_hr\\_payroll'),
            ('state', '=', 'installed'),
        ])

    @classmethod
    def _get_payroll_l10n_countries(cls):
        modules = cls._get_payroll_l10n_modules()
        country_codes = {name[5:7].upper() for name in modules.mapped('name')}
        return cls.env['res.country'].search([('code', 'in', country_codes)])

    def test_new_employee_group_hr_user(self):
        for country in self._get_payroll_l10n_countries():
            company = self.env['res.company'].create({
                'name': f'Company {country.name}',
                'country_id': country.id,
            })
            self.res_users_hr_officer.company_ids |= company
            self.res_users_hr_officer.company_id = company

            with Form(self.env['hr.employee'].with_user(self.res_users_hr_officer)) as employee_form:
                employee_form.name = f'Employee {country.name}'
                employee_form.contract_date_start = '2020-01-01'
                employee_form.company_id = company
                employee_form.save()

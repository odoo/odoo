# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLuPayrollCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.lux_company = cls.env['res.company'].create({
            'name': 'Letzebuerg Corp.',
            'currency_id': cls.env.ref('base.EUR').id,
            'country_id': cls.env.ref('base.lu').id,
            'l10n_lu_official_social_security': 12345678987,
            'l10n_lu_seculine': 999999999,
        })

        cls.env.user.company_ids |= cls.lux_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.lux_company.ids))

        cls.employee_david = cls.env['hr.employee'].create({
            'name': 'david',
            'private_country_id': cls.env.ref('base.lu').id,
            'company_id': cls.lux_company.id,
            'identification_id': 111111111,
        })
        cls.contract_david = cls.env['hr.contract'].create({
            'name': 'david Contract',
            'employee_id': cls.employee_david.id,
            'company_id': cls.lux_company.id,
            'structure_type_id': cls.env.ref('l10n_lu_hr_payroll.structure_type_employee_lux').id,
            'date_start': '2021-1-1',
            'wage': 6000.0,
            'state': 'open',
        })

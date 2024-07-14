# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'K.S.A. - Payroll',
    'countries': ['sa'],
    'author': 'Odoo PS',
    'category': 'Human Resources/Payroll',
    'description': """
Kingdom of Saudi Arabia Payroll and End of Service rules.
===========================================================

    """,
    'license': 'OEEL-1',
    'depends': ['hr_payroll', 'l10n_sa'],
    'data': [
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_contract_view.xml',
    ],
    'auto_install': True,
}

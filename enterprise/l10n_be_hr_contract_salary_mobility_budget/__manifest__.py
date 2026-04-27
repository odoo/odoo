# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator (Belgium) - Mobility Budget',
    'category': 'Human Resources',
    'summary': 'Salary Package Configurator',
    'depends': [
        'l10n_be_hr_contract_salary',
    ],
    'data': [
        "data/hr_contract_salary_benefit_data.xml",
        "report/report_payslip_templates.xml",
        "views/hr_contract_views.xml",
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'l10n_be_hr_contract_salary_mobility_budget/static/src/**/*',
        ],
    }
}

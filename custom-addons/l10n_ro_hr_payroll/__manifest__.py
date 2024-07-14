# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Romania - Payroll',
    'countries': ['ro'],
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': [
        'hr_payroll',
        'hr_contract_reports',
        'hr_work_entry_holidays',
        'hr_payroll_holidays',
    ],
    'data': [
        'views/report_payslip_templates.xml',
        'views/hr_payroll_report.xml',
        'views/hr_contract_views.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_data.xml',
    ],
    'demo': [
        'data/l10n_ro_hr_payroll_demo.xml',
    ],
    'license': 'OEEL-1',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Kenya - Payroll SHIF',
    'countries': ['ke'],
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Kenyan Payroll Rules
========================================
This module is only temporary, its purpose is to make the transition from NHIF to SHIF in stables versions (17.0, 18.0).
    """,
    'depends': ['l10n_ke_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'security/l10n_ke_hr_payroll_shif_security.xml',
        'data/hr_rule_parameters_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_employee_views.xml',
        'wizards/l10n_ke_hr_payroll_shif_report_wizard_views.xml',
        'views/l10n_ke_hr_payroll_shif_menus.xml'
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

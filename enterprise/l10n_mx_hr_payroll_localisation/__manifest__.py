# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mexico - Payroll - Localisation',
    'category': 'Human Resources/Payroll',
    'depends': ['l10n_mx_hr_payroll'],
    'version': '1.0',
    'description': 'Add models and fields for complete mexican localisation',
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/l10n_mx_hr_infonavit_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_payroll_structure_type_views.xml',
        'views/report_payslip_templates.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

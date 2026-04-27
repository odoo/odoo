# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Belgium - Payroll - Export to Group S",
    'countries': ['be'],
    'summary': "Export Work Entries to Group S",
    'description': "Export Work Entries to Group S",
    'category': "Human Resources",
    'version': '1.0',
    'depends': ['l10n_be_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_work_entry_type_data.xml',
        'data/hr_payroll_dashboard_warning_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_payroll_export_group_s_views.xml',
    ],
    'demo': [
        'data/l10n_be_hr_payroll_group_s_demo.xml',
    ],
    'license': 'OEEL-1',
}

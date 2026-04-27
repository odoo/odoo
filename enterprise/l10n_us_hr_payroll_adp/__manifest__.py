# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "United States - Payroll - Export to ADP",
    'countries': ['us'],

    'summary': "Export Work Entries to ADP",

    'description': "Export Work Entries to ADP",

    'category': "Human Resources",
    'version': '1.0',

    'depends': ['l10n_us_hr_payroll'],

    'data': [
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_work_entry_views.xml',
        'views/l10n_us_adp_export_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
{
    'name': "Belgium - Payroll - Export to SD Worx",
    'countries': ['be'],

    'summary': "Export Work Entries to SD Worx",

    'description': "Export Work Entries to SD Worx",

    'category': "Human Resources",
    'version': '1.0',

    'depends': ['l10n_be_hr_payroll'],

    'data': [
        'security/ir.model.access.csv',
        'data/hr_work_entry_type_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/l10n_be_export_sdworx_leaves_wizard_views.xml',
    ],
    'demo': [
        'data/l10n_be_hr_payroll_sd_worx_demo.xml',
    ],
    'license': 'OEEL-1',
}

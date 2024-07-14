# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Belgian Payroll',
    'countries': ['be'],
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Store employee 281.10 and 281.45 forms in the Document app',
    'description': """
Employee 281.10 and 281.45 forms will be automatically integrated to the Document app.
""",
    'website': ' ',
    'depends': ['documents_hr_payroll', 'l10n_be_hr_payroll'],
    'data': [
        'views/hr_payroll_281_45_wizard_views.xml',
        'views/hr_payroll_281_10_wizard_views.xml',
        'views/l10n_be_individual_account_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

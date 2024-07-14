# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Hong Kong Payroll',
    'countries': ['hk'],
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Store ir56 forms in the Document app',
    'description': """
Employee ir56 forms will be automatically integrated to the Document app.
""",
    'website': ' ',
    'depends': ['documents_hr_payroll', 'l10n_hk_hr_payroll'],
    'data': [
        'views/l10n_hk_ir56b_views.xml',
        'views/l10n_hk_ir56e_views.xml',
        'views/l10n_hk_ir56f_views.xml',
        'views/l10n_hk_ir56g_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Expenses',
    'version': '1.0',
    'description': """GST Expenses""",
    'category': 'Localization',
    'depends': [
        'l10n_in',
        'hr_expense',
    ],
    'data': [
        'views/hr_expense_views.xml',
    ],
    'auto_install': True,
}

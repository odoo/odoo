# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2019 - Blanco Martín & Asociados. https://www.bmya.cl
{
    'name': 'Chile - Expenses Fix',
    'version': "1.0",
    'description': """
Chilean expenses fix. When installing hr_expense application it fixes the Journal Type to allow registration of
expenses in miscellaneous Journals.
    """,
    'author': 'Blanco Martín & Asociados',
    'website': 'https://www.odoo.com/documentation/14.0/applications/finance/accounting/fiscal_localizations/localizations/chile.html',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'hr_expense',
        'l10n_cl',
    ],
    'active': True,
    'auto_install': True,
}

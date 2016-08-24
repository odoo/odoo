# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United States - Accounting',
    'version': '1.1',
    'category': 'Localization',
    'description': """
United States - Chart of accounts.
==================================
    """,
    'depends': ['l10n_generic_coa', 'report'],
    'data': [
        'data/res_company.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

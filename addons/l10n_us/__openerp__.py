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
        'views/res_config_view.xml',
        'data/res_company_data.xml',
    ],
}

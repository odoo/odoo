# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - Real Estates",
    'countries': ['es'],
    'description': """
This module allows the user to add real estate related data to the Spanish localization and generates a mod 347 report.
    """,

    'category': 'Accounting/Localizations',
    'version': '0.1',
    'depends': ['l10n_es_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_invoice_views.xml',
        'views/real_estates_data_views.xml',
        'wizard/aeat_boe_export_wizards.xml',
        'data/mod347.xml',
    ],
    'license': 'OEEL-1',
}

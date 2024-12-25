# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Saudi Arabia - E-Invoicing Branches',
    'icon': '/l10n_sa/static/description/icon.png',
    'version': '0.1',
    'depends': [
        'l10n_sa_edi',
    ],
    'author': 'Odoo',
    'summary': """
        E-Invoicing, Branches
    """,
    'description': """
Allows the support for ZATCA branches multiple commercial registrations
    """,
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'data': [
        'views/res_config_settings_views.xml',
        'views/account_journal_views.xml',
    ],
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Germany - Accounting',
    "version": "2.0",
    'author': 'openbig.org',
    'website': 'http://www.openbig.org',
    'category': 'Accounting/Localizations',
    'description': """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03.
==============================================================================

German accounting chart and localization.
    """,
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'data/account_account_tags_data.xml',
        'data/menuitem_data.xml',
        'views/account_view.xml',
        'views/res_company_views.xml',
        'report/din5008_report.xml',
        'data/report_layout.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_de/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}

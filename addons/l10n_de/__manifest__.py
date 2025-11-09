# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Germany - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['de'],
    'author': 'openbig.org (http://www.openbig.org)',
    'version': '3.0',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/germany.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03 oder SKR04.
=========================================================================================

German accounting chart and localization.
By default, the audit trail is enabled for GoBD compliance.
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'l10n_din5008',
        'account',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_account_tags_data.xml',
        'views/account_view.xml',
        'views/res_company_views.xml',
        'wizard/account_secure_entries_wizard.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}

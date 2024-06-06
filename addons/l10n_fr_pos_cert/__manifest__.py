# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - VAT Anti-Fraud Certification for Point of Sale (CGI 286 I-3 bis)',
    'icon': '/l10n_fr/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
This add-on brings the technical requirements of the French regulation CGI art. 286, I. 3° bis that stipulates certain criteria concerning the inalterability, security, storage and archiving of data related to sales to private individuals (B2C).
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Install it if you use the Point of Sale app to sell to individuals.

The module adds following features:

    Inalterability: deactivation of all the ways to cancel or modify key data of POS orders, invoices and journal entries

    Security: chaining algorithm to verify the inalterability

    Storage: automatic sales closings with computation of both period and cumulative totals (daily, monthly, annually)

    Access to download the mandatory Certificate of Conformity delivered by Odoo SA (only for Odoo Enterprise users)
""",
    'depends': ['l10n_fr', 'point_of_sale'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/pos_views.xml',
        'views/account_sale_closure.xml',
        'views/pos_inalterability_menuitem.xml',
        'views/res_config_settings_views.xml',
        'report/pos_hash_integrity.xml',
        'data/account_sale_closure_cron.xml',
        'security/ir.model.access.csv',
        'security/account_closing_intercompany.xml',
    ],
    'post_init_hook': '_setup_inalterability',
    'assets': {
        'point_of_sale.assets': [
            'l10n_fr_pos_cert/static/src/js/**/*',
            'l10n_fr_pos_cert/static/src/css/pos.css',
            'l10n_fr_pos_cert/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}

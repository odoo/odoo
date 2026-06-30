# -*- coding: utf-8 -*-
{
    'name': "Egypt E-Invoicing",
    'summary': """
            Egypt Tax Authority Invoice Integration
        """,
    'description': """
Egypt Tax Authority Invoice Integration
==============================================================================
Integrates with the ETA portal to automatically send and sign the Invoices to the Tax Authority.
    """,
    'author': 'Odoo S.A., Plementus',
    'category': 'account',
    'version': '0.2',
    'license': 'LGPL-3',
    'depends': ['account_edi', 'l10n_eg'],
    'icon': '/account/static/description/l10n.png',
    'countries': ['eg'],
    'data': [
        'data/account_edi_data.xml',
        'data/l10n_eg_edi.activity.type.csv',
        'data/l10n_eg_edi.uom.code.csv',
        'data/uom.uom.csv',
        'security/ir.model.access.csv',
        'security/eta_thumb_drive_security.xml',
        'views/uom_uom_view.xml',
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
        'views/eta_thumb_drive.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_view.xml',
        'views/report_invoice.xml',
        'data/res_country_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_eg_edi_eta/static/src/**/*.js',
        ],
    },
    'external_dependencies': {
        'python': ['asn1crypto'],
        'apt': {
            'asn1crypto': 'python3-asn1crypto',
        },
    },
}

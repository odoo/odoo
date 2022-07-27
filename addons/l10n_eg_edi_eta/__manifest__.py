# -*- coding: utf-8 -*-
{
    'name': "Egyptian E-Invoice Integration",
    'summary': """
            Egyptian Tax Authority Invoice Integration
        """,
    'description': """
       This module integrate with the ETA Portal to automatically sign and send your invoices to the tax Authority.
       Special thanks to Plementus <info@plementus.com> for their help in developing this module.
    """,
    'author': 'odoo',
    'website': 'https://www.odoo.com',
    'category': 'account',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['account_edi', 'l10n_eg'],
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
        'data/res_country_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_eg_edi_eta/static/src/js/sign_invoice.js',
        ],
    },
    'external_dependencies': {
        'python': ['asn1crypto'],
    },
}

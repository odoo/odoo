# -*- coding: utf-8 -*-
{
    'name': "Egyptian E-Receipts Integration",
    'summary': """
            Egyptian Tax Authority E-Receipts Integration
        """,
    'description': """
       This module integrate with the ETA Portal to automatically sign and send your receipts to the tax Authority.
    """,
    'author': 'odoo',
    'website': 'https://www.odoo.com',
    'category': 'account',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['l10n_eg_edi_eta', 'point_of_sale'],
    'data': [
        'data/ir_cron.xml',
        'data/ir_actions_server.xml',
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_eg_pos_edi_eta/static/src/scss/pos.scss',
            'l10n_eg_pos_edi_eta/static/src/js/models.js',
            'l10n_eg_pos_edi_eta/static/src/js/ReceiptScreen.js',
            'l10n_eg_pos_edi_eta/static/src/js/OrderReceipt.js',
            'l10n_eg_pos_edi_eta/static/src/js/PaymentScreen.js'
        ],
        'web.assets_qweb': [
            'l10n_eg_pos_edi_eta/static/src/xml/**/*'
        ],
    },

}

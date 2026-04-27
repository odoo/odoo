# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mexican Localization for the Point of Sale',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    """,
    'depends': [
        'l10n_mx_edi',
        'point_of_sale',
    ],
    'data': [
        'views/pos_payment_method_views.xml',
        'views/pos_order_views.xml',

        'wizard/l10n_mx_edi_global_invoice_create.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'account/static/src/components/document_state/*',
            'l10n_mx_edi_pos/static/src/**/*',
            'l10n_mx/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_mx_edi_pos/static/tests/tours/invoice_order_tour.js',
            'l10n_mx_edi_pos/static/tests/tours/invoice_previous_order_tour.js',
            'l10n_mx_edi_pos/static/tests/tours/l10n_mx_pos_tour.js',
            'l10n_mx_edi_pos/static/tests/tours/refund_order_tour.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

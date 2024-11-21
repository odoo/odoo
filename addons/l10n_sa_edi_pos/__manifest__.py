# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Saudi Arabia - E-invoicing (Simplified)',
    'icon': '/l10n_sa/static/description/icon.png',
    'version': '0.1',
    'depends': [
        'l10n_sa_pos',
        'l10n_sa_edi',
    ],
    'author': 'Odoo S.A.',
    'summary': """
        ZATCA E-Invoicing, support for PoS
    """,
    'description': """
E-invoice implementation for Saudi Arabia; Integration with ZATCA (POS)
    """,
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'assets': {
        'point_of_sale.assets': [
            'l10n_sa_edi_pos/static/src/js/pos_models.js',
            'l10n_sa_edi_pos/static/src/js/PaymentScreen.js',
        ],
    }
}

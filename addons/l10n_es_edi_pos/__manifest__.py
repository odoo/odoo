# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - Point of Sale EDI Common",
    'countries': ['es'],
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': "Common features for the Spanish EDI Point of Sale modules (SII, TicketBAI, Veri*Factu)",
    'description': """
Shared base for the Spanish EDI Point of Sale modules.

It decides which fiscal system handles the Point of Sale orders of a company
(the "POS fiscal mode") when several EDI modules are installed, and holds the
logic that is common to all of them. It does not depend on any EDI module:
each EDI POS module depends on this one and declares its own mode.
    """,
    'depends': [
        'l10n_es',
        'point_of_sale',
    ],
    'data': [
        'receipt/pos_order_receipt.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_edi_pos/static/src/**/*',
        ],
    },
    'post_init_hook': '_l10n_es_edi_pos_post_init',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

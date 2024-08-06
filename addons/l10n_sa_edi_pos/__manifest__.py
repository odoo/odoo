# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Saudi Arabia - E-invoicing (Simplified)',
    'countries': ['sa'],
    'version': '0.1',
    'depends': [
        'l10n_sa_pos',
        'l10n_sa_edi',
    ],
    'author': 'Odoo',
    'summary': """
        ZATCA E-Invoicing, support for PoS
    """,
    'description': """
        E-invoice implementation for the Kingdom of Saudi Arabia (PoS)
    """,
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_sa_edi_pos/static/src/overrides/**/*.js',
        ],
    }
}

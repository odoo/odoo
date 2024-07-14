# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Point of Sale',
    'version': '1.0',
    'countries': ['ec'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
This module brings the technical requirements for the Ecuadorian regulations.
Install this if you are using the Point of Sale app in Ecuador.
    """,
    'depends': [
        'l10n_ec_edi',
        'point_of_sale',
    ],
    'data': [
        'views/pos_payment_method_views.xml',
        'views/report_invoice.xml',
        'views/ticket_validation_screen.xml',
        'data/l10n_ec.sri.payment.csv',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_ec_edi_pos/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

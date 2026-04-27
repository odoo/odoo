# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Point of Sale',
    'version': '1.0',
    'countries': ['ec'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
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
        'web.assets_tests': [
            'l10n_ec_edi_pos/static/tests/tours/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

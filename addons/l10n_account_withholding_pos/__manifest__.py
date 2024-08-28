# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Invoicing - Payment Withholding in PoS',
    'version': "1.0",
    'description': """Add support for the withholding tax module in the PoS.""",
    'category': 'Accounting/Localizations',
    'depends': ['l10n_account_withholding', 'point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_account_withholding/static/src/helpers/*.js',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

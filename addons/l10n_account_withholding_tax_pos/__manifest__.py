# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Withholding Tax on Payment - PoS',
    'version': "1.0",
    'description': """Add support for the withholding tax module in the PoS.""",
    'category': 'Accounting/Localizations',
    'depends': ['l10n_account_withholding_tax', 'point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_account_withholding_tax/static/src/helpers/*.js',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

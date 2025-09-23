# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Poland - Taxable Supply Date',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Extension for Poland - Accounting to add support for taxable supply date
========================================================================
    """,
    'depends': ['l10n_pl'],
    'auto_install': True,
    'data': [
        'views/account_move_views.xml',
        'views/report_invoice.xml',
    ],
    'license': 'LGPL-3',
}

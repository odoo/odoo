# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentina - Payment Withholdings',
    'description': """Allows to register withholdings during the payment of an invoice.""",
    'author': 'ADHOC SA',
    'countries': ['ar'],
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_ar',
        'l10n_latam_check',
        'l10n_account_withholding_tax',
    ],
    'data': [
        'data/earnings_table_data.xml',
        'security/ir.access.csv',
        'views/account_tax_views.xml',
        'views/res_partner_view.xml',
        'views/l10n_ar_earnings_scale_view.xml',
        'wizards/account_payment_register_views.xml',
    ],
    'license': 'LGPL-3',
}

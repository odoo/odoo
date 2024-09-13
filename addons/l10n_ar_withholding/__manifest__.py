# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Argentina - Payment Withholdings',
    'version': "1.0",
    'description': """Allows to register withholdings during the payment of an invoice.""",
    'author': 'ADHOC SA',
    'countries': ['ar'],
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_ar',
        'l10n_latam_check',
        'l10n_account_withholding',
    ],
    'data': [
        'wizards/account_payment_register_views.xml',
    ],
    'installable': True,
    'post_init_hook': '_l10n_ar_withholding_post_init',
    'license': 'LGPL-3',
}

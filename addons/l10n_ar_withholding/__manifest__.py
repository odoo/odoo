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
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/account_payment_view.xml',
        'views/report_payment_receipt_templates.xml',
        'views/res_config_settings.xml',
        'views/res_partner_view.xml',
        'views/l10n_ar_earnings_scale_view.xml',
        'wizards/account_payment_register_views.xml',
        'data/earnings_table_data.xml',
        'security/ir.access.csv',
    ],
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Withholding Tax on Payment',
    'description': """Allows to register withholding taxes during the payment of an invoice or bill.""",
    'category': 'Accounting/Localizations',
    'depends': ['account'],
    'data': [

        'views/account_payment_views.xml',
        'views/account_tax_views.xml',
        'views/report_payment_receipt_templates.xml',
        'views/res_config_settings.xml',

        'wizards/account_payment_register_views.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_account_withholding_tax/static/src/helpers/*.js',
        ],
        'web.assets_frontend': [
            'l10n_account_withholding_tax/static/src/helpers/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

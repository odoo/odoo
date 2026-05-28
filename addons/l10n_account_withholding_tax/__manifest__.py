# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Withholding Tax',
    'description': """Allows users to manage withholding taxes on invoices, bills, and payments.""",
    'category': 'Accounting/Localizations',
    'depends': ['account'],
    'data': [
        'views/report_invoice.xml',
        'views/account_move_views.xml',
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
            'l10n_account_withholding_tax/static/src/components/**/*'
        ],
        'web.assets_frontend': [
            'l10n_account_withholding_tax/static/src/helpers/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Invoicing - Payment Withholding',
    'version': "1.0",
    'description': """Allows to register withholding taxes during the payment of an invoice.""",
    'category': 'Accounting/Localizations',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',

        'views/account_fiscal_position_tax_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_view.xml',
        'views/account_portal_templates.xml',
        'views/account_tax_views.xml',
        'views/report_payment_receipt_templates.xml',
        'views/res_config_settings.xml',

        'wizards/account_payment_register_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_account_withholding/static/src/js/account_portal_sidebar.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

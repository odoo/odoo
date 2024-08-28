# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Invoicing - Payment Withholding',
    'version': "1.0",
    'description': """Allows to register withholding taxes during the payment of an invoice or bill.""",
    'category': 'Accounting/Localizations',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',

        'views/account_payment_view.xml',
        'views/account_tax_views.xml',
        'views/product_view.xml',
        'views/report_payment_receipt_templates.xml',
        'views/res_config_settings.xml',

        'wizards/account_payment_register_views.xml',
    ],
    'installable': True,
    'post_init_hook': '_l10n_account_wth_post_init',
    'license': 'LGPL-3',
}

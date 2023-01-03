# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment - Account",
    'category': 'Accounting/Accounting',
    'summary': "Enable customers to pay invoices on the portal and post payments when transactions are processed.",
    'version': '2.0',
    'depends': ['account', 'payment'],
    'auto_install': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        'views/account_payment_menus.xml',
        'views/account_portal_templates.xml',
        'views/payment_templates.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',

        'wizards/account_payment_register_views.xml',
        'wizards/payment_link_wizard_views.xml',
        'wizards/payment_refund_wizard_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'account_payment/static/src/js/payment_form.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Invoicing',
    'version': '1.1',
    'category': 'Accounting/Accounting',
    'sequence': 30,
    'summary': 'Invoices, Payments, Follow-ups & Bank synchronization (Enterprise)',
    'icon': '/account/static/description/icon.png',
    'description': """
Invoicing Access Rights
========================
It gives the Administrator user access to important invoicing features such as bank recon and payment follow-up.

""",
    'website': 'https://www.odoo.com/app/accounting',
    'depends': ['account', 'mail_enterprise', 'web_tour'],
    'data': [
        'data/ir_cron.xml',
        'data/digest_data.xml',
        'data/account_accountant_tour.xml',

        'security/ir.model.access.csv',
        'security/account_accountant_security.xml',

        'views/account_account_views.xml',
        'views/account_fiscal_year_view.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/account_reconcile_views.xml',
        'views/account_reconcile_model_views.xml',
        'views/account_accountant_menuitems.xml',
        'views/digest_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/bank_rec_widget_views.xml',
        'views/report_invoice.xml',

        'wizard/account_change_lock_date.xml',
        'wizard/account_auto_reconcile_wizard.xml',
        'wizard/account_reconcile_wizard.xml',
        'wizard/reconcile_model_wizard.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_account_accountant_post_init',
    'uninstall_hook': "uninstall_hook",
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_accountant/static/src/js/tours/account_accountant.js',
            'account_accountant/static/src/components/**/*',
            'account_accountant/static/src/**/*.xml',
        ],
        'web.assets_unit_tests': [
            'account_accountant/static/tests/**/*',
            ('remove', 'account_accountant/static/tests/tours/**/*'),
        ],
        'web.assets_tests': [
            'account_accountant/static/tests/tours/**/*',
        ],
    }
}

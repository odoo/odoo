# -*- coding: utf-8 -*-
{
    'name': "Online Bank Statement Synchronization",
    'summary': "This module is used for Online bank synchronization.",

    'description': """
With this module, users will be able to link bank journals to their
online bank accounts (for supported banking institutions), and configure
a periodic and automatic synchronization of their bank statements.
    """,

    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account_accountant'],

    'data': [
        'data/config_parameter.xml',
        'data/ir_cron.xml',
        'data/mail_activity_type_data.xml',
        'data/sync_reminder_email_template.xml',

        'security/ir.model.access.csv',
        'security/account_online_sync_security.xml',

        'views/account_online_sync_views.xml',
        'views/account_bank_statement_view.xml',
        'views/account_journal_view.xml',
        'views/account_online_sync_portal_templates.xml',
        'views/account_journal_dashboard_view.xml',

        'wizard/account_bank_selection_wizard.xml',
        'wizard/account_journal_missing_transactions.xml',
        'wizard/account_bank_statement_line.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_online_synchronization/static/src/components/**/*',
            'account_online_synchronization/static/src/js/odoo_fin_connector.js',
        ],
        'web.assets_frontend': [
            'account_online_synchronization/static/src/js/online_sync_portal.js',
        ],
        'web.qunit_suite_tests': [
            'account_online_synchronization/static/tests/helpers/*.js',
            'account_online_synchronization/static/tests/*.js',
        ],
    }
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expenses - Invoicing',
#    'version': '1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Record accounting entries for your expenses',
    'description': """
Manage expenses by Employees
============================

This application allows you to create the accounting entries related to your expenses receipts. Allowing you to set-up preset of taxes per categories of expenses
Employee can encode their own expenses and the validation flow puts it automatically in the accounting after validation by managers.


The whole flow is implemented as:
---------------------------------
* Draft expense
* Submitted by the employee to his manager
* Approved by his manager
* Validation by the accountant and accounting entries creation

This module also uses analytic accounting and is compatible with the invoice on timesheet module so that you are able to automatically re-invoice your customers' expenses if your work by project.
    """,
    'depends': ['account', 'hr_expense'],
    'data': [
        'security/ir_access.xml',
        'security/ir.access.csv',

        'data/mail_message_subtype_data.xml',

        'views/product_product_views.xml',
        'views/hr_expense_views.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/res_config_settings_views.xml',

        'report/hr_expense_report.xml',

        'wizard/hr_expense_split_views.xml',
        'wizard/hr_expense_split_wizard_views.xml',
    ],
    'demo': ['demo/account_journal_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'account_hr_expense/static/src/scss/hr_expense.css',
            'account_hr_expense/static/src/views/list_patch.js',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    "auto_install": True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

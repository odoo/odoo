# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expenses',
    'version': '2.1',
    'category': 'Human Resources/Expenses',
    'sequence': 70,
    'summary': 'Submit, validate and reinvoice employee expenses',
    'description': """
Manage expenses by Employees
============================

This application allows you to manage your employees' daily expenses. It gives you access to your employees’ fee notes and give you the right to complete and validate or refuse the notes.
Employee can encode their own expenses and allow manager to review and validate them.


The whole flow is implemented as:
---------------------------------
* Draft expense
* Submitted by the employee to his manager
* Approved by his manager

This module is compatible with the Sale, Project and Payroll app in order to re-invoice expenses to your customers and reimburse your employees through their payslipsx.
    """,
    'website': 'https://www.odoo.com/app/expenses',
    'depends': ['analytic', 'hr', 'product', 'web_tour'],
    'data': [
        'security/hr_expense_security.xml',
        'security/ir.access.csv',

        'data/digest_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_alias_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates.xml',
        'data/hr_expense_data.xml',
        'data/hr_expense_tour.xml',

        'views/product_product_views.xml',
        'views/hr_expense_views.xml',
        'views/mail_activity_views.xml',
        'views/hr_department_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',

        'wizard/hr_expense_refuse_reason_views.xml',
        'wizard/hr_expense_approve_duplicate_views.xml',
        'wizard/hr_expense_split_wizard_views.xml',
        'wizard/hr_expense_split_views.xml',

        'report/hr_expense_report.xml',
    ],
    'demo': ['demo/hr_expense_demo.xml'],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'hr_expense/static/src/components/*.js',
            'hr_expense/static/src/components/*.xml',
            'hr_expense/static/src/mixins/*.js',
            'hr_expense/static/src/views/*.js',
            'hr_expense/static/src/views/*.xml',
            'hr_expense/static/src/webclient/**/*',
            'hr_expense/static/src/scss/hr_expense.scss',
            'hr_expense/static/src/js/tours/*.js',
            'hr_expense/static/src/js/web/*.js',
        ],
        'web.assets_tests': [
            'hr_expense/static/tests/tours/*.js',
        ],
        'web.report_assets_common': [
            'hr_expense/static/src/scss/hr_expense.scss',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

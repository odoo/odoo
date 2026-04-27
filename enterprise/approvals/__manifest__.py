# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Approvals',
    'version': '1.1',
    'category': 'Human Resources/Approvals',
    'sequence': 190,
    'summary': 'Create and validate approvals requests',
    'description': """
This module manages approvals workflow
======================================

This module manages approval requests like business trips,
out of office, overtime, borrow items, general approvals,
procurements, contract approval, etc.

According to the approval type configuration, a request
creates next activities for the related approvers.
    """,
    'depends': ['mail', 'hr', 'product'],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',

        'data/approval_category_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_message_subtype_data.xml',

        'views/approval_category_views.xml',
        'views/approval_category_approver_views.xml',
        'views/approval_product_line_views.xml',
        'views/approval_products_views.xml',
        'views/approval_request_template.xml',
        'report/approval_request_report.xml',
        'views/approval_request_views.xml',
        'views/res_users_views.xml',
    ],
    'demo':[
        'data/approval_demo.xml',
    ],
    'application': True,
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'approvals/static/src/**',
        ],
        'web.assets_tests': [
            'approvals/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'approvals/static/tests/**/*',
            ('remove', 'approvals/static/tests/tours/**/*'),
        ],
    },
    'license': 'OEEL-1',
}

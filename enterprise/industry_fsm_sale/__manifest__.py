# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Field Service - Sale",
    'summary': "Schedule and track onsite operations, invoice time and material",
    'description': """
Create Sales order with timesheets and products from tasks
    """,
    'category': 'Services/Field Service',
    'version': '1.0',
    'depends': ['industry_fsm', 'sale_timesheet_enterprise'],
    'data': [
        'data/industry_fsm_data.xml',
        'report/report_project_task_user_fsm_views.xml',
        'report/worksheet_custom_report_templates.xml',
        'views/project_task_views.xml',
        'views/product_product_views.xml',
        'views/project_project_views.xml',
        'views/sale_order_views.xml',
        "views/project_sharing_views.xml",
        'views/project_portal_templates.xml',
    ],
    'demo': [
        'data/industry_fsm_demo.xml',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_backend': [
            'industry_fsm_sale/static/src/components/**/*',
            'industry_fsm_sale/static/src/js/tours/**/*',
        ],
        'web.assets_tests': [
            'industry_fsm_sale/static/tests/tours/**/*',
        ],
        'web.assets_frontend': [
            'industry_fsm_sale/static/src/js/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'industry_fsm_sale/static/tests/product_catalog.test.js',
            'industry_fsm_sale/static/tests/industry_fsm_sale_mock_model.js',
        ],
    },
    'license': 'OEEL-1',
}

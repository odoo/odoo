# -*- coding: utf-8 -*-
{
    'name': "Rental Stock Management",

    'summary': "Allows use of stock application to manage rentals inventory",

    'description': """

    """,

    'website': "https://www.odoo.com",

    'category': 'Sales/Sales',
    'version': '1.0',

    'depends': ['sale_renting', 'sale_stock'],

    'data': [
        'security/sale_stock_renting_security.xml',
        'data/rental_stock_data.xml',
        'wizard/rental_processing_views.xml',
        'wizard/stock_picking_return_views.xml',
        'report/rental_schedule_views.xml',
        'report/rental_report_views.xml',
        'report/rental_order_report_templates.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/res_company_views.xml',
    ],
    'demo': [
        'data/rental_stock_demo.xml',
    ],
    'auto_install': True,
    'post_init_hook': '_ensure_rental_stock_moves_consistency',
    'assets': {
        'web.assets_backend': [
            'sale_stock_renting/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sales',
    'version': '1.2',
    'category': 'Sales/Sales',
    'summary': 'Sales internal machinery',
    'description': """
This module contains all the common features of Sales Management and eCommerce.
    """,
    'depends': ['sales_team', 'payment', 'portal', 'utm'],
    'data': [
        'security/sale_security.xml',
        'security/ir.model.access.csv',
        'report/sale_report.xml',
        'report/sale_report_views.xml',
        'report/sale_report_templates.xml',
        'report/invoice_report_templates.xml',
        'report/report_all_channels_sales_views.xml',
        'data/ir_sequence_data.xml',
        'data/mail_data_various.xml',
        'data/mail_template_data.xml',
        'data/mail_templates.xml',
        'data/sale_data.xml',
        'wizard/sale_make_invoice_advance_views.xml',
        'views/sale_views.xml',
        'views/crm_team_views.xml',
        'views/res_partner_views.xml',
        'views/mail_activity_views.xml',
        'views/variant_templates.xml',
        'views/sale_portal_templates.xml',
        'views/sale_onboarding_views.xml',
        'views/res_config_settings_views.xml',
        'views/payment_templates.xml',
        'views/payment_views.xml',
        'views/product_views.xml',
        'views/product_packaging_views.xml',
        'views/utm_campaign_views.xml',
        'wizard/sale_order_cancel_views.xml',
        'wizard/sale_payment_link_views.xml',
    ],
    'demo': [
        'data/product_product_demo.xml',
        'data/sale_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'sale/static/src/scss/sale_onboarding.scss',
            'sale/static/src/scss/product_configurator.scss',
            'sale/static/src/js/sale.js',
            'sale/static/src/js/tours/sale.js',
            'sale/static/src/js/product_configurator_widget.js',
            'sale/static/src/js/sale_order_view.js',
            'sale/static/src/js/product_discount_widget.js',
        ],
        'web.report_assets_common': [
            'sale/static/src/scss/sale_report.scss',
        ],
        'web.assets_frontend': [
            'sale/static/src/scss/sale_portal.scss',
            'sale/static/src/js/sale_portal_sidebar.js',
            'sale/static/src/js/payment_form.js',
        ],
        'web.assets_tests': [
            'sale/static/tests/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'sale/static/tests/product_configurator_tests.js',
            'sale/static/tests/sales_team_dashboard_tests.js',
        ],
    },
    'post_init_hook': '_synchronize_cron',
    'license': 'LGPL-3',
}

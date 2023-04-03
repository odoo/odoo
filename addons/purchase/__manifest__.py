# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase',
    'version': '1.2',
    'category': 'Inventory/Purchase',
    'sequence': 35,
    'summary': 'Purchase orders, tenders and agreements',
    'website': 'https://www.odoo.com/app/purchase',
    'depends': ['account'],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'views/account_move_views.xml',
        'data/purchase_data.xml',
        'data/ir_cron_data.xml',
        'report/purchase_reports.xml',
        'views/purchase_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'report/purchase_bill_views.xml',
        'report/purchase_report_views.xml',
        'data/mail_templates.xml',
        'data/mail_template_data.xml',
        'views/portal_templates.xml',
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml',
        'views/product_packaging_views.xml',
        'views/analytic_account_views.xml',
    ],
    'demo': [
        'data/purchase_demo.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'purchase/static/src/toaster_button/*',
            'purchase/static/src/views/*.js',
            'purchase/static/src/js/tours/purchase.js',
            'purchase/static/src/js/tours/purchase_steps.js',
            'purchase/static/src/**/*.xml',
        ],
        'web.assets_frontend': [
            'purchase/static/src/js/purchase_datetimepicker.js',
            'purchase/static/src/js/purchase_portal_sidebar.js',
        ],
    },
    'license': 'LGPL-3',
}

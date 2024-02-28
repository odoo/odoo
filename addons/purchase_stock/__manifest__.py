# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Stock',
    'version': '1.2',
    'category': 'Inventory/Purchase',
    'sequence': 60,
    'summary': 'Purchase Orders, Receipts, Vendor Bills for Stock',
    'depends': ['stock_account', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_stock_data.xml',
        'data/mail_templates.xml',
        'report/vendor_delay_report.xml',
        'views/purchase_views.xml',
        'views/stock_views.xml',
        'views/stock_rule_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/stock_lot_views.xml',
        'report/purchase_report_views.xml',
        'report/purchase_report_templates.xml',
        'report/report_stock_forecasted.xml',
        'report/report_stock_rule.xml',
        'wizard/stock_replenishment_info.xml'
    ],
    'demo': [
        'data/purchase_stock_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_create_buy_rules',
    'assets': {
        'web.assets_backend': [
            'purchase_stock/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}

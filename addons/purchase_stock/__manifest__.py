# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Stock',
    'version': '1.2',
    'category': 'Purchases',
    'sequence': 60,
    'summary': 'Purchase Orders, Receipts, Vendor Bills for Stock',
    'description': "",
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['stock_account', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_stock_data.xml',
        'data/mail_data.xml',
        'views/purchase_views.xml',
        'views/stock_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_production_lot.xml',
        'report/purchase_report_views.xml',
        'report/purchase_report_templates.xml',
    ],
    'demo': [
        'data/purchase_stock_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}

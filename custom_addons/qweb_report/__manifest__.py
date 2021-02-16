{
    'name': 'Qweb PDF report',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 12,
    'description': """Different types of reporting""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'sale_management',
            'purchase',
            'product',
            'sale_stock',
            'stock',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        'report/paperformal.xml',
        'security/ir.model.access.csv',
        'report/sale_a4_portrait.xml',
        'report/sale_a4_portrait_both.xml',
        'report/sale_a4_portrait_inherit.xml',
        'report/inherit_my_report.xml',
        'report/purchase_a4_portrait.xml',
        'report/product_stock_inventory.xml',
        'wizard/stock_inventory_report_wizard.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


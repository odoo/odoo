# -*- coding: utf-8 -*-

{
    'name': 'Sales Addons',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 15,
    'summary': 'Advance Stamped Receipt',
    'description': """
Manage Generation of Advance Stamped Receipt for Sales Module
=============================================================

This application allows you to create Advance Stamped Receipt for Customers and to generate reports which is useful in many Sales oriented organisations.

Preferences (only with Sales Management installed)
------------------------------------------------------
This module is a additional feature to the Sales Management Module.
    """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale'],
    'data': [
        'report/report_advance_stamped_receipt.xml',
        'views/advance_stamped_receipt.xml',
    ],
    'demo': [
        'data/sale_demo.xml',
        'data/product_product_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

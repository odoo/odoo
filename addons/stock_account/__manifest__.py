# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WMS Accounting',
    'version': '1.1',
    'summary': 'Inventory, Logistic, Valuation, Accounting',
    'description': """
WMS Accounting module
======================
This module makes the link between the 'stock' and 'account' modules and allows you to create accounting entries to value your stock movements

Key Features
------------
* Stock Valuation (periodical or automatic)
* Invoice from Picking

Dashboard / Reports for Warehouse Management includes:
------------------------------------------------------
* Stock Inventory Value at given date (support dates in the past)
    """,
    'depends': ['stock', 'account'],
    'category': 'Supply Chain/Inventory',
    'sequence': 16,
    'data': [
        'security/stock_account_security.xml',
        'security/ir.model.access.csv',
        'data/stock_account_data.xml',
        'views/account_account_views.xml',
        'views/stock_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice.xml',
        'views/stock_quant_views.xml',
        'views/product_views.xml',
        'views/product_value_views.xml',
        'views/stock_location_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'wizard/stock_inventory_adjustment_name_views.xml',
        'report/account_invoice_report_view.xml',
        'report/stock_avco_audit_report_views.xml',
        'report/stock_valuation_report.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_post_init_hook',
    'assets': {
        'web.assets_backend': [
            'stock_account/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

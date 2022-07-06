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
    'category': 'Hidden',
    'sequence': 16,
    'data': [
        'security/stock_account_security.xml',
        'security/ir.model.access.csv',
        'data/stock_account_data.xml',
        'views/stock_account_views.xml',
        'views/res_config_settings_views.xml',
        'data/product_data.xml',
        'views/report_invoice.xml',
        'views/stock_valuation_layer_views.xml',
        'views/stock_quant_views.xml',
        'views/product_views.xml',
        'wizard/stock_request_count.xml',
        'wizard/stock_valuation_layer_revaluation_views.xml',
        'wizard/stock_quantity_history.xml',
        'report/report_stock_forecasted.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_configure_journals',
    'assets': {
        'web.assets_backend': [
            'stock_account/static/src/js/report_stock_forecasted.js',
        ],
        'web.assets_qweb': [
            'stock_account/static/src/xml/inventory_report.xml',
        ],
    },
    'license': 'LGPL-3',
}

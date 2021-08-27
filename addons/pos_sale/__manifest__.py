# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_sale',
    'version': '1.1',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Link module between Point of Sale and Sales',
    'description': """

This module adds a custom Sales Team for the Point of Sale. This enables you to view and manage your point of sale sales with more ease.
""",
    'depends': ['point_of_sale', 'sale_management'],
    'data': [
        'data/pos_sale_data.xml',
        'security/pos_sale_security.xml',
        'security/ir.model.access.csv',
        'views/point_of_sale_report.xml',
        'views/sale_order_views.xml',
        'views/pos_order_views.xml',
        'views/sales_team_views.xml',
        'views/pos_config_views.xml',
        'views/stock_template.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_sale/static/src/css/pos_sale.css',
            'pos_sale/static/src/js/models.js',
            'pos_sale/static/src/js/SetSaleOrderButton.js',
            'pos_sale/static/src/js/OrderManagementScreen/MobileSaleOrderManagementScreen.js',
            'pos_sale/static/src/js/OrderManagementScreen/SaleOrderFetcher.js',
            'pos_sale/static/src/js/OrderManagementScreen/SaleOrderList.js',
            'pos_sale/static/src/js/OrderManagementScreen/SaleOrderManagementControlPanel.js',
            'pos_sale/static/src/js/OrderManagementScreen/SaleOrderManagementScreen.js',
            'pos_sale/static/src/js/OrderManagementScreen/SaleOrderRow.js',
            'pos_sale/static/src/js/ProductScreen.js',
        ],
        'web.assets_qweb': [
            'pos_sale/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}

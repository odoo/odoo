# -*- coding: utf-8 -*-
{
    'name': "Import Export Inventory Report",

    'summary': """
        Inventory Report with total initial, qty in, qty out, balance""",

    'description': """
        
    """,
    "license": "LGPL-3",
    'author': "Jason Vu",
    'website': "https://github.com/longvm91/odoo-custom-modules/tree/16.0/imex_inventory_report",
    'email': "longvm91@gmail.com",
    'category': 'Warehouse',
    'version': '16.0.1.3.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'stock_account', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/imex_inventory_report_views.xml',
        'reports/imex_inventory_details_report_views.xml',
        'wizard/imex_inventory_report_wizard_view.xml',
    ],
    'images': ['static/img/report1.png', 'static/img/report2.png'],
    "assets": {
        "web.assets_backend": [
            "imex_inventory_report/static/src/css/**/*",
            "imex_inventory_report/static/src/js/**/*",
        ],
    },
    "installable": True,
}

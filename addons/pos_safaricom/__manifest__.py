{
    'name': 'POS Safaricom',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with the Safaricom Payment Provider',
    'depends': ['point_of_sale'],
    'data': [
        "views/pos_payment_method_views.xml",
        'security/ir.model.access.csv',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_safaricom/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "pos_safaricom/static/tests/unit/**/*",
        ],
    },
    "author": "Odoo S.A.",
    'license': 'LGPL-3',
}

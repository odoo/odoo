{
    'name': 'POS Safaricom',
    'version': '1.0',
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
        "web.assets_tests": [
            "pos_safaricom/static/tests/tours/**/*",
        ],
    },
    "author": "Odoo S.A.",
    'license': 'LGPL-3',
    'installable': True,
}

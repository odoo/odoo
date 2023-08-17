# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Purchase Product Configurator",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "Configure your products",
    'description': """
Technical module:
The main purpose is to override the purchase_order view to allow configuring products in the PO form.
    """,

    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_product_configurator/static/src/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

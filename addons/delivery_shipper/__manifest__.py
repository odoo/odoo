# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Shipper Shipping",
    'description': """
<>
=======================================================
<>
    """,
    'category': 'Inventory/Delivery',
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'base_address_extended'],
    'data': [
        # 'data/res.city.csv',
        # 'data/district.csv',
        # 'data/area.csv',
        'data/shipper_data.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/portal.xml',
        # 'wizard/choose_delivery_carrier_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # 'delivery_shipper/static/src/js/website_sale_shipper.js',
            'delivery_shipper/static/src/js/portal.js',
            # 'delivery_shipper/static/src/xml/website_sale_shipper.xml',
            # 'delivery_shipper/static/src/scss/website_sale_shipper.scss',
        ],
    },
    'post_init_hook': 'post_init',
    'license': 'OEEL-1',
}

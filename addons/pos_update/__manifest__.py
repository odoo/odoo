{
    'name': 'Point Of Sale Update',
    'version': '1.0',
    'description': 'Remove Barcode field if product type is "combo" (in point_of_sale)',
    'depends': ['point_of_sale'],
    'data': [
        'views/product_views.xml',
    ],
    'assets': {
    'point_of_sale._assets_pos': [
        'pos_update/static/src/**/*'
    ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

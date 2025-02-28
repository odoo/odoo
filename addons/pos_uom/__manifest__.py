{
    'name': 'POS - Second Unit of Measurement',
    'version': '1.0',
    'depends': ['point_of_sale'],
    'description': "Second UoM for POS module",
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_uom/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}

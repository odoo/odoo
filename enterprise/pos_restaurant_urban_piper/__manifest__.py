{
    'name': 'POS Restaurant Urban Piper',
    'category': 'Sales/Point of Sale',
    'description': """
This module integrates with UrbanPiper to receive and manage orders from various food delivery platforms such as Swiggy and Zomato.
    """,
    'depends': ['pos_restaurant', 'pos_urban_piper'],
    'assets': {
        'web.assets_backend': [
        ],
        'point_of_sale._assets_pos': [
            'pos_restaurant_urban_piper/static/src/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}

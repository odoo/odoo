{
    'name': 'POS UrbanPiper - Uber Eats',
    'category': 'Sales/Point of Sale',
    'description': """
This module integrates with UrbanPiper to receive and manage orders from Uber Eats.
    """,
    'depends': ['pos_urban_piper'],
    'data': [
        'data/pos_delivery_provider_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_urban_piper_ubereats/static/src/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}

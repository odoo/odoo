{
    'name': 'POS UrbanPiper - Zomato',
    'category': 'Sales/Point of Sale',
    'description': """
This module integrates with UrbanPiper to receive and manage orders from Zomato.
    """,
    'depends': ['pos_urban_piper'],
    'data': [
        'data/pos_delivery_provider_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

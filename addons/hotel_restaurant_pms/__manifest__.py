{
    'name': 'Hotel and Restaurant PMS with Fiscalization',
    'version': '1.0',
    'author': 'Ally Elvis Nzeyimana',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/hotel_room_views.xml',
        'views/hotel_guest_views.xml',
        'views/hotel_booking_views.xml',
        'views/restaurant_menu_views.xml',
        'views/restaurant_order_views.xml',
        'views/pos_sync_views.xml',
    ],
    'installable': True,
    'application': True,
}

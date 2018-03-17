# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Booking Management',
    'version': '10.0.1.0.0',
    'author': 'Odoo Community Association (OCA), Serpent Consulting \
                Services Pvt. Ltd., Odoo S.A.',
    'category': 'Generic Modules/Hotel Booking',
    'license': 'AGPL-3',
    'depends': ['hotel', 'stock', 'mail'],
    'demo': ['views/hotel_reservation_data.xml', ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hotel_reservation_wizard.xml',
        'report/hotel_reservation_report.xml',
        'views/hotel_reservation_sequence.xml',
        'views/hotel_reservation_view.xml',
        'data/hotel_scheduler.xml',
        'views/email_temp_view.xml',
        'views/report_checkin.xml',
        'views/report_checkout.xml',
        'views/max_room.xml',
        'views/room_res.xml',
        'views/room_summ_view.xml',
    ],
    'js': ['static/src/js/hotel_room_summary.js', ],
    'qweb': ['static/src/xml/hotel_room_summary.xml'],
    'css': ['static/src/css/room_summary.css'],
    'installable': True,
    'auto_install': False,
}

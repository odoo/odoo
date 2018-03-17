# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Booking Management - Reporting',
    'version': '10.0.1.0.0',
    'author': 'Odoo Community Association (OCA), Serpent Consulting\
                Services Pvt. Ltd., Odoo S.A.',
    'website': 'http://www.serpentcs.com',
    'depends': ['hotel_reservation'],
    'license': 'AGPL-3',
    'category': 'Generic Modules/Hotel Booking',
    'data': [
        'security/ir.model.access.csv',
        'views/report_hotel_reservation_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

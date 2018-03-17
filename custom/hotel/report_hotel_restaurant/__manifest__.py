# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Restaurant Management - Reporting',
    'version': '10.0.1.0.0',
    'author': 'Odoo Community Association (OCA), Serpent Consulting\
                Services Pvt. Ltd., Odoo S.A.',
    'website': 'http://www.serpentcs.com',
    'depends': ['hotel_restaurant', 'report_hotel_reservation'],
    'category': 'Generic Modules/Hotel Restaurant',
    'license': 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/report_hotel_restaurant_view.xml',
    ],
    'installable': True,
}

# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel POS Restaurant Management',
    'version': '10.0.1.0.0',
    'author': 'Serpent Consulting Services Pvt. Ltd., OpenERP SA',
    'category': 'Generic Modules/Hotel Restaurant Management',
    'website': 'http://www.serpentcs.com',
    'depends': ['hotel'],
    'license': 'AGPL-3',
    'demo': ['views/hotel_pos_data.xml'],
    'data': ['security/ir.model.access.csv',
             'views/pos_restaurent_view.xml',
             'views/hotel_pos_report.xml',
             'views/report_pos_management.xml',
             'wizard/hotel_pos_wizard.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'images': ['static/description/HotelPOSRestaurant.png'],
    'auto_install': False,
    'installable': True
}

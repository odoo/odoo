# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Real Estate',
    'version': '1.2',  
    'summary': 'Advertise and sell your properties with Odoo',
    'description': "Fully managed all you properties in Odoo with little setup.",
    'depends': [
        'base_setup',
    ], 
    'installable': True,
    'application': True,
    'auto_install': False,
    'data':[
        'data\state_property_views.xml',
        'data\estate_menus.xml',
        'security\ir.model.access.csv',
    ],
}
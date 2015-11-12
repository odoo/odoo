# -*- coding: utf-8 -*-

{
    'name': 'Equipments',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Track equipment and manage maintenance requests.""",
    'author': 'Odoo S.A.',
    'depends': ['mail'],
    'summary': 'Equipments, Assets, Internal Hardware, Allocation Tracking',
    'data': [
        'security/equipment.xml',
        'security/ir.model.access.csv',
        'data/equipment_data.xml',
        'views/equipment_views.xml',
        'views/maintenance_dashboard.xml',
    ],
    'demo': ['data/equipment_demo.xml'],
    'installable': True,
    'application': True,
}

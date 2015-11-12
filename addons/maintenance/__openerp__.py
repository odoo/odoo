# -*- coding: utf-8 -*-

{
    'name': 'Equipments',
    'version': '1.0',
    'sequence': 125,
    'category': 'Human Resources',
    'description': """
        Track equipment and manage maintenance requests.""",
    'depends': ['mail'],
    'summary': 'Equipments, Assets, Internal Hardware, Allocation Tracking',
    'data': [
        'security/maintenance.xml',
        'security/ir.model.access.csv',
        'data/maintenance_data.xml',
        'views/maintenance_views.xml',
        'views/maintenance_templates.xml',
    ],
    'demo': ['data/maintenance_demo.xml'],
    'installable': True,
    'application': True,
}

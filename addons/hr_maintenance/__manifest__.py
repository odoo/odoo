# -*- coding: utf-8 -*-

{
    'name': 'Maintenance - HR',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Bridge between HR and Maintenance.""",
    'depends': ['hr', 'maintenance'],
    'summary': 'Equipments, Assets, Internal Hardware, Allocation Tracking',
    'data': [
        'security/equipment.xml',
        'views/maintenance_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}

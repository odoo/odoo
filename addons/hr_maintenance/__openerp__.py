# -*- coding: utf-8 -*-

{
    'name': 'HR - Equipments',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Track equipment and manage maintenance requests.""",
    'author': 'Odoo S.A.',
    'depends': ['hr', 'maintenance'],
    'summary': 'Equipments, Assets, Internal Hardware, Allocation Tracking',
    'data': [
        'security/equipment.xml',
        'views/equipment_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto-install': True,
}

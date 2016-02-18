# -*- coding: utf-8 -*-

{
    'name': 'Equipments',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Track employees' equipment and manage maintenance requests.""",
    'author': 'Odoo S.A.',
    'depends': ['hr'],
    'summary': 'Equipments, Assets, Internal Hardware, Allocation Tracking',
    'data': [
        'security/hr_equipment.xml',
        'security/ir.model.access.csv',
        'data/hr_equipment_data.xml',
        'views/res_config_views.xml',
        'views/hr_equipment_views.xml',
    ],
    'demo': ['data/hr_equipment_demo.xml'],
    'installable': True,
    'application': True,
}

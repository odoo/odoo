# -*- coding: utf-8 -*-

{
    'name': 'Track Employees Equipment',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Track employees' equipment and manage its allocation """,
    'author': 'Odoo S.A.',
    'depends': ['hr'],
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

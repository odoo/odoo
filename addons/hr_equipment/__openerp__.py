# -*- coding: utf-8 -*-

{
    'name': 'IT Assets',
    'version': '1.0',
    'sequence': 125,
    'description': """
        Track employees' IT assets: computers, printers, software licenses and manage makntenance requests.""",
    'author': 'Odoo S.A.',
    'depends': ['hr'],
    'summary': 'Equipments, IT Assets, Internal Hardware',
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

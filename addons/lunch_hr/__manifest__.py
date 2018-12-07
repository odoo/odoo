# -*- coding: utf-8 -*-

{
    'name': 'Lunch HR',
    'sequence': 120,
    'version': '1.0',
    'depends': ['lunch', 'hr'],
    'category': 'Human Resources',
    'summary': 'Handle lunch orders of your employees',
    'description': """""",
    'data': [
        'views/lunch_product_views.xml',
        'views/lunch_supplier_views.xml',
    ],
    'demo': ['data/lunch_hr_demo.xml',],
    'auto_install': True,
    'installable': True,
    'application': False,
}

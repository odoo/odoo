# -*- coding: utf-8 -*-

{
    'name': "Custom Delivery Split",
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': """Delivery Split will works based on Location Divide and Full.""",
    'description': """ Delivery Split Will be created when pick is created Based on Full and 
    Divide Location. First it will check nested location for Divide and then it will take quantities
    from Full nested location""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'website': "https://www.shiperoo.com",
    'depends': ['sale_management', 'stock'],
    'data': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

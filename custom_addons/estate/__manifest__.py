# -*- coding: utf-8 -*-
{
    'name': "estate",
    'version': '1.0',
    'author': "Nahuel",
    'description': "Modulo para Real Estate.",
    'sequence' : -100,
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/estate.xml',
        'views/estate_menu.xml',
        # 'views/view_estate.xml',
        #'views/estate_form.xml',
        'views/estate_type.xml',

    ],
    'application': True,
    'installable': True,


}

# -*- coding: utf-8 -*-
{
    'name': "pos_color",

    'summary': """
       """,

    'description': """
        
    """,

    'website': "",


    'category': 'Point of Sale',
    'version': '14.0.0.3',

    # any module necessary for this one to work correctly
    'depends': ['point_of_sale'],

    # always loaded
    'data': [


        'views/templates.xml',
    ],

    'qweb': [
        'static/src/xml/*.xml',
    ],
    "auto_install": False,
    "installable": True,
}

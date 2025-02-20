# -*- coding: utf-8 -*-
{
    'name': "Tilsol - Login Page Customization",
    'summary': """ Login Page Customization """,
    'description': """ Login Page Customization """,
    'author': "Tilsol",

    # Categories can be used to filter modules in modules listing

    # for the full list
    'category': 'developers',
    'version': '17.0',

    # any module necessary for this one to work correctly
    'depends': ['web'],

    # always loaded
    'data': [
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    "application": True,
    "installable": True,
    'auto_install': True,
}
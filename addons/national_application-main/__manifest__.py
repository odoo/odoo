# -*- coding: utf-8 -*-
{
    'name': "national_application",

    'summary': "National ID Application",

    'description': """
    National ID Application (Assignment 2)
    """,

    'author': "Immy",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','website'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'application': True,
   
}


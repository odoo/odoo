# -*- coding: utf-8 -*-
{
    'name': "Awesome Dashboard",

    'summary': """
        Demo addon for the Odoo JS Framework
    """,

    'description': """
        Demo addon for the Odoo JS Framework
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com/",
    'category': 'Tutorials',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],

    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'awesome_dashboard/static/src/**/*',
        ],
    },
    'license': 'AGPL-3'
}

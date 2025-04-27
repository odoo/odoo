# -*- coding: utf-8 -*-
{
    'name': "Awesome Clicker",

    'summary': """
        Starting module for "Master the Odoo web framework, chapter 1: Build a Clicker game"
    """,

    'description': """
        Starting module for "Master the Odoo web framework, chapter 1: Build a Clicker game"
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com/",
    'category': 'Tutorials/AwesomeClicker',
    'version': '0.1',
    'application': True,
    'installable': True,
    'depends': ['base', 'web'],

    'data': [],
    'assets': {
        'web.assets_backend': [
            'awesome_clicker/static/src/**/*',
        ],

    },
    'license': 'AGPL-3'
}

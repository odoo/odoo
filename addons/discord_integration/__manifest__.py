# -*- coding: utf-8 -*-
{
    'name': "Discord Integration",

    'summary': "Integration between Discord and Odoo's discuss",

    'description': """
This modules relays all of the messages from discord to discuss and viceversa.
    """,

    'author': "My Company",

    'category': 'Productivity/Discuss',
    'version': '0.1',

    'depends': [
        'base',
        'mail',
    ],

    'data': [
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}

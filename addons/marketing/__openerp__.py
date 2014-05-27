# -*- coding: utf-8 -*-

{
    'name': 'Marketing',
    'version': '1.1',
    'depends': ['base', 'base_setup'],
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'description': """
Menu for Marketing.
===================

Contains the installer for marketing-related modules.
    """,
    'website': 'http://www.openerp.com',
    'data': [
        'marketing_view.xml',
        'res_config_view.xml',
    ],
    'demo': [ ],
    'installable': True,
    'auto_install': False,
    'images': ['images/config_marketing.jpeg'],
}

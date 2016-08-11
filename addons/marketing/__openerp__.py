# -*- coding: utf-8 -*-

{
    'name': 'Marketing',
    'version': '1.1',
    'depends': ['base', 'base_setup'],
    'category': 'Hidden',
    'description': """
Menu for Marketing.
===================

Contains the installer for marketing-related modules.
    """,
    'website': 'https://www.odoo.com/page/mailing',
    'data': [
        'security/marketing_security.xml',
        'marketing_view.xml',
        'res_config_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
{
    'name' : 'LinkedIn Integration',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
Odoo Web LinkedIn module.
============================
This module provides the Integration of the LinkedIn with Odoo.
        """,
    'author': 'Odoo SA',
    'website': 'http://odoo.com',
    'data': [
        'views/web_linkedin_view.xml',
        'views/web_linkedin.xml',
    ],
    'depends' : ['web','crm', 'web_kanban'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}

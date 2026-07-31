# -*- coding: utf-8 -*-
{
    'name': 'CAMTEL Core',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'CAMTEL Base Module - Template for Custom Extensions',
    'description': """
CAMTEL Core Module
==================
Minimal foundation module for CAMTEL customizations.
Ready to extend with custom functionality as needed.
    """,
    'author': 'CAMTEL',
    'website': 'https://www.camtel.cm',
    'depends': ['base', 'web', 'stock'],
    'data': [
        'security/camtel_security.xml',
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

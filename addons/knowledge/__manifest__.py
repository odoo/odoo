# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Knowledge",
    'summary': 'Centralise, manage, share and grow your knowledge library',
    'description': "Centralise, manage, share and grow your knowledge library",
    'category': 'Knowledge',
    'version': '0.1',
    'depends': ['web', 'mail'],
    'data': [
        'data/knowledge_data.xml',
        'views/knowledge_views.xml',
        'views/knowledge_templates.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

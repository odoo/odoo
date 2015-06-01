# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name' : 'Knowledge Management System',
    'version' : '1.0',
    'depends' : ['base','base_setup'],
    'author' : 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'description': """
Installer for knowledge-based Hidden.
=====================================

Makes the Knowledge Application Configuration available from where you can install
document and Wiki based Hidden.
    """,
    'website': 'https://www.odoo.com',
    'data': [
        'security/knowledge_security.xml',
        'security/ir.model.access.csv',
        'knowledge_view.xml',
        'res_config_view.xml',
    ],
    'demo': ['knowledge_demo.xml'],
    'installable': True,
    'auto_install': False,
}

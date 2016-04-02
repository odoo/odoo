# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Initial Setup Tools',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module helps to configure the system at the installation of a new database.
================================================================================

Shows you a list of applications features to install from.

    """,
    'depends': ['base', 'web_kanban'],
    'data': [
        'security/ir.model.access.csv',
        'base_setup_views.xml',
        'res_config_view.xml',
        'res_partner_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

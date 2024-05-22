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
    'depends': ['base', 'web'],
    'data': [
        'data/base_setup_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/assets.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,

    'qweb': [
        'static/src/xml/res_config_dev_tool.xml',
        'static/src/xml/res_config_edition.xml',
        'static/src/xml/res_config_invite_users.xml',
    ],

    
    'license': 'LGPL-3',
}

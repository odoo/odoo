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
        ],
    'demo': [],
    'installable': True,
    'auto_install': False,

    'assets': {
        'web.assets_backend': [
            'base_setup/static/src/scss/settings.scss',
            'base_setup/static/src/js/res_config_dev_tool.js',
            'base_setup/static/src/js/res_config_edition.js',
            'base_setup/static/src/js/res_config_invite_users.js',
        ],
        'web.assets_qweb': [
            'base_setup/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}

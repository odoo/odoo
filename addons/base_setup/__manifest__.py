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
        'data/res.country.csv',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        ],
    'installable': True,
    'post_init_hook': 'auto_install_l10n',
    'license': 'LGPL-3',
}

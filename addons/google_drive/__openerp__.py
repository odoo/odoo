# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Drive™ integration',
    'version': '0.2',
    'category': 'Tools',
    'description': """
Integrate google document to Odoo record.
============================================

This module allows you to integrate google documents to any of your Odoo record quickly and easily using OAuth 2.0 for Installed Applications,
You can configure your google Authorization Code from Settings > General Settings by clicking on "Generate Google Authorization Code"
""",
    'depends': ['base_setup', 'google_account'],
    'data': [
        'data/google_drive_data.xml',
        'security/ir.model.access.csv',
        'views/res_config_user_view.xml',
        'views/google_drive_views.xml',
        'views/base_config_setting_views.xml',
    ],
    'demo': [
        'data/google_drive_demo.xml'
    ],
    'installable': True,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Base - Module Install Request',
    'category': 'Hidden',
    'depends': ['mail'],
    'description': """
Allow internal users requesting a module installation
=====================================================
    """,
    'auto_install': True,
    'data':[
        'security/ir.model.access.csv',
        'wizard/base_module_install_request_views.xml',
        'data/mail_template_data.xml',
        'data/mail_templates_module_install.xml',
        'views/ir_module_module_views.xml',
    ],
    'license': 'LGPL-3',
    'post_init_hook': '_auto_install_apps'
}

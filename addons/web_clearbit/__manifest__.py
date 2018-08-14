# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Partner autocomplete',
    'description': "Auto-complete partner companies' data",
    'depends': ['web', 'base_setup'],
    'data': [
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/web_clearbit_templates.xml'
    ],
    'qweb': [
        'static/src/xml/web_clearbit.xml'
    ],
    'auto_install': True,
    'external_dependencies': {
        'python': ['clearbit'],
    },
}

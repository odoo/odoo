# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'KPI Digests',
    'category': 'Marketing',
    'description': """
Send KPI Digests periodically
=============================
""",
    'version': '1.0',
    'depends': [
        'mail',
        'portal'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/digest_template_data.xml',
        'data/digest_data.xml',
        'data/ir_cron_data.xml',
        'data/res_config_settings_data.xml',
        'views/digest_views.xml',
        'views/digest_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
}

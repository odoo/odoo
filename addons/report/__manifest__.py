# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Report',
    'category': 'Base',
    'summary': 'Hidden',
    'description': """
Report
        """,
    'depends': ['base', 'web', 'base_setup'],
    'data': [
        'data/report_paperformat_data.xml',
        'security/ir.model.access.csv',
        'views/layout_templates.xml',
        'views/report_paperformat_views.xml',
        'views/report_templates.xml',
        'views/base_config_settings_views.xml',
        'views/ir_actions_report_views.xml',
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}

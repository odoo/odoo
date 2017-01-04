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
    'demo': [
        'data/report_demo.xml',
    ],
    'data': [
        'data/report_paperformat_data.xml',
        'security/ir.model.access.csv',
        'views/report_paperformat_views.xml',
        'views/base_config_settings_views.xml',
        'views/ir_actions_report_views.xml',
        'views/res_company_view.xml',
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'auto_install': True,
}

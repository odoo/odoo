# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Report',
    'category': 'Base',
    'summary': 'Report',
    'description': """
Report
        """,
    'depends': ['base', 'web'],
    'data': [
        'views/layout_templates.xml',
        'views/report_paperformat_views.xml',
        'data/report_paperformat_data.xml',
        'security/ir.model.access.csv',
        'views/report_templates.xml',
        'views/res_company_views.xml',
        'views/ir_actions_report_views.xml',
    ],
    'auto_install': True,
}

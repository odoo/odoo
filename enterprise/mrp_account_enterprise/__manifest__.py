# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting - MRP',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Analytic accounting in Manufacturing',
    'description': """
Analytic Accounting in MRP
==========================

* Cost structure report
""",
    'website': 'https://www.odoo.com/app/manufacturing',
    'depends': ['mrp_account'],
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_account_enterprise_security.xml',
        'views/mrp_account_view.xml',
        'views/cost_structure_report.xml',
        'reports/mrp_report_views.xml',
        ],
    'demo': ['demo/mrp_account_demo.xml'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.report_assets_common': [
            'mrp_account_enterprise/static/src/scss/cost_structure_report.scss',
        ],
    }
}

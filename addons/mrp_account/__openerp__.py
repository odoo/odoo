# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'MRP Accounting',
    'version': '1.0',
    'category': 'Manufacturing',
    'description': """
This adds some analytic accounting to manufacturing
    """,
    'website': 'https://www.odoo.com/page/manufacturing',
    'depends': ['mrp', 'account'],
    'data': [
                'views/mrp_account_view.xml',
                'views/mocost_templates.xml',
                'report/mrp_report_menu.xml'
            ],
    'demo': ['data/mrp_account_demo.xml'],
    'installable': True,
}

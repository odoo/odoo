# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Contracts Management',
    'version': '1.1',
    'category': 'Sales Management',
    'description': """
This module is for modifying account analytic view to show important data to project manager of services companies.
===================================================================================================================

Adds menu to show relevant information to each manager.You can also view the report of account analytic summary user-wise as well as month-wise.
""",
    'author': 'Camptocamp / Odoo',
    'website': 'https://www.odoo.com/page/billing',
    'depends': ['hr_timesheet_invoice', 'sale'], #although sale is technically not required to install this module, all menuitems are located under 'Sales' application
    'data': [
        'security/ir.model.access.csv',
        'security/account_analytic_analysis_security.xml',
        'views/sale_contract_view.xml',
        'data/sale_contract_cron.xml',
        'views/res_config_view.xml',
        'views/account_analytic_analysis.xml',
        'views/product_template_view.xml',
    ],
    'demo': ['demo/sale_contract_demo.xml'],
    'test': ['test/account_analytic_analysis.yml'],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Budget Management',
    'category': 'Accounting/Accounting',
    'description': """
Use budgets to compare actual with expected revenues and costs
--------------------------------------------------------------
""",
    'depends': ['accountant', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'security/account_budget_security.xml',
        'wizards/budget_split_wizard_view.xml',
        'views/budget_analytic_views.xml',
        'views/budget_line_view.xml',
        'views/account_analytic_account_views.xml',
        'views/purchase_views.xml',
        'reports/budget_report_view.xml',
    ],
    'demo': ['data/account_budget_demo.xml'],
    'license': 'OEEL-1',
    'post_init_hook': 'post_init_hook',
}

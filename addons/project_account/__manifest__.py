# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Project - Account",
    'summary': "project profitability items computation",
    'description': """
Allows the computation of some section for the project profitability
==================================================================================================
This module allows the computation of the 'Vendor Bills', 'Other Costs' and 'Other Revenues' section for the project profitability, in the project update view.
""",
    'category': 'Accounting/Accounting',
    'depends': ['account', 'project'],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/account_analytic_line_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/project_sharing_project_task_views.xml',
    ],
}

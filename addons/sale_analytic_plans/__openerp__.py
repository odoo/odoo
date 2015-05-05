# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Analytic Distribution',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
The base module to manage analytic distribution and sales orders.
=================================================================

Using this module you will be able to link analytic accounts to sales orders.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale', 'account_analytic_plans'],
    'data': ['sale_analytic_plans_view.xml','res_config.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Purchase Analytic Plans',
    'version': '1.0',
    'category': 'Purchase Management',
    'description': """
The base module to manage analytic distribution and purchase orders.
====================================================================

Allows the user to maintain several analysis plans. These let you split a line
on a vendor purchase order into several accounts and analytic plans.
    """,
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['purchase', 'account_analytic_plans'],
    'data': ['purchase_analytic_plans_view.xml', 'res_config.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

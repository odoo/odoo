# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs for company\'s branches',
    'version': '1.0',
    'description': """
    This module is a patch that stores the company_id field on the landed cost model.
    That way, it is possible to create/use landed costs from a branch.
    """,
    'depends': ['stock_landed_costs'],
    'category': 'Inventory/Inventory',
    'sequence': 16,
    'installable': True,
    'auto_install': True,
    'post_init_hook': '_stock_landed_costs_company_post_init',
    'license': 'LGPL-3',
}

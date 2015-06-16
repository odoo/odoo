# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Contracts Management: hr_expense link',
    'version': '1.1',
    'category': 'Hidden',
    'description': """
This module is for modifying account analytic view to show some data related to the hr_expense module.
======================================================================================================
""",
    'author': 'OpenERP S.A.',
    'website': 'https://www.odoo.com/',
    'depends': ['hr_expense','account_analytic_analysis'],
    'data': ['analytic_contract_hr_expense_view.xml'],
    'demo': [],
    'installable': True,
    'auto_install': True,
}

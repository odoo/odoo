# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Intrastat & EC Sales List',
    'category': 'Accounting',
    'description': """
A module that adds intrastat reports.
=====================================

This module gives the details of the goods traded between the countries of
European Union.""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/country_data.xml',
        'data/transaction_data.xml',
        'data/transport_data.xml',
        'data/code_data.xml',
        'data/intrastat_export.xml',
        'views/account_intrastat_code_view.xml',
        'views/product_view.xml',
        'views/res_country_view.xml',
        'views/account_invoice_view.xml',
        'views/res_company_view.xml',
        'views/account_intrastat_wizard_view.xml',
    ],
}

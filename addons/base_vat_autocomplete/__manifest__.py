# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'VAT Number Autocomplete',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
Auto-Complete Addresses based on VAT numbers
============================================

    This module requires the python library stdnum to work.
    """,
    'depends': ['base_vat'],
    'data': [
        'views/res_partner_views.xml',
        'views/res_company_view.xml',
    ],
    'auto_install': True
}

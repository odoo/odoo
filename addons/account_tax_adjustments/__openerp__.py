# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting Tax Adjustments',
    'version': '1.1',
    'category': 'Accounting & Finance',
    'description': """
Accounting Tax Adjustments.
===========================

This module adds a wizard to deal with manual Tax adjustments, to manually correct the VAT declaration through a miscellaneous operation for example.

The correct definition of an adjustment tax is
- type_tax_use: none
- amount_type: fixed
- amount: 0
- tags: a grid used in your vat report for manual correction.

    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account'],
    'data': [
        'views/tax_adjustments.xml',
        'wizard/wizard_tax_adjustments_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

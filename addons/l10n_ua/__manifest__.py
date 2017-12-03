# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ukraine - Accounting',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'version': '1.1',
    'description': """
Ukrainian Accounting.
=====================

This is base module for Ukrainian accounting.

Charts of Accounts is provided by dedicated module:
---------------------------------------------------
    * l10n_ua_psbo - for COA based on national standards.

    * l10n_ua_ifrs - for COA based on IFRS.
    """,
    'category': 'Localization',
    'depends': ['account'],
    'data': [
        'data/menuitem_data.xml',
        'data/account_account_tag_data.xml',
        'data/account_tax_tag_data.xml',
        'data/account_tax_group_data.xml',
        'views/partner_view.xml',
    ],
}

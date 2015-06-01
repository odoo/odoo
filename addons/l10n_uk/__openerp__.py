# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2011 Smartmode LTD (<http://www.smartmode.co.uk>).

{
    'name': 'UK - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the latest UK OpenERP localisation necessary to run OpenERP accounting for UK SME's with:
=================================================================================================
    - a CT600-ready chart of accounts
    - VAT100-ready tax structure
    - InfoLogic UK counties listing
    - a few other adaptations""",
    'author': 'SmartMode LTD',
    'website': 'http://www.smartmode.co.uk',
    'depends': ['base_iban', 'base_vat'],
    'data': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
        'data/res.country.state.csv',
        'l10n_uk_wizard.xml',
    ],
    'demo' : ['demo/demo.xml'],
    'installable': False,
}

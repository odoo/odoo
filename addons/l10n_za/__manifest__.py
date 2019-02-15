# -*- encoding: utf-8 -*-

# Copyright (C) 2017 Paradigm Digital (<http://www.paradigmdigital.co.za>).

{
    'name': 'South Africa - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the latest basic South African localisation necessary to run Odoo in ZA:
================================================================================
    - a generic chart of accounts
    - SARS VAT Ready Structure""",
    'author': 'Paradigm Digital',
    'website': 'https://www.paradigmdigital.co.za',
    'depends': ['account', 
                'base_vat'
    ],
    'data': [
        'data/account.account.tag.csv',
        'data/account.tax.group.csv',
        'data/l10n_za_chart_data.xml',
        'data/account_template.xml',
        'data/account.tax.template.csv',
        'data/account_chart_template.yml',
        
    ],
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright: (C) 2012 - Mentis d.o.o., Dravograd

{
    "name": "Slovenian - Accounting",
    "version": "1.1",
    "author": "Mentis d.o.o.",
    "website": "http://www.mentis.si",
    'category': 'Accounting/Localizations/Account Charts',
    "description": "Kontni načrt za gospodarske družbe",
    "depends": [
        "account",
        "base_iban",
    ],
    "data": [
        "data/l10n_si_chart_data.xml",
        "data/account.account.template.csv",
        "data/account.chart.template.csv",
        "data/account.tax.group.csv",
        "data/account_tax_report_data.xml",
        "data/account_tax_data.xml",
        "data/account.fiscal.position.template.csv",
        "data/account.fiscal.position.account.template.csv",
        "data/account.fiscal.position.tax.template.csv",
        "data/account_chart_template_data.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

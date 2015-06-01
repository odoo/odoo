# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright: (C) 2012 - Mentis d.o.o., Dravograd

{
    "name": "Slovenian - Accounting",
    "version": "1.2",
    "author": "Mentis d.o.o.",
    "website": "http://www.mentis.si",
    "category": "Localization/Account Charts",
    "description": " ",
    "depends": ["account", "base_iban", "base_vat", "account_cancel"],
    "description": "Kontni načrt za gospodarske družbe",
    "data": [
        "data/account.account.type.csv",
        "data/account.account.template.csv",
        "data/account.chart.template.csv",
        "data/account.tax.template.csv",
        "data/account.fiscal.position.template.csv",
        "data/account.fiscal.position.account.template.csv",
        "data/account.fiscal.position.tax.template.csv",
        "l10n_si_wizard.xml"
    ],
    "installable": False,
}

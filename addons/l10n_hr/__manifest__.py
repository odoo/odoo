# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Goran Kliska, Ivana Boras
# mail:   goran.kliska(AT)slobodni-programi.hr , ivana.boras@uvid.hr
# Copyright (C) 2011- Slobodni programi d.o.o., Zagreb,
# Copyright (C) 2021- Uvid d.o.o., Zagreb
# Contributions:
#           Tomislav Bošnjaković, Storm Computers d.o.o. :
#              - account types
#           Ivana Šimek, Uvid d.o.o. :
#              - account types, fiscal positions, taxes

{
    "name": "Croatia - Accounting (RRIF 2021)",
    "description": """
Croatian localization.
======================

Author: Goran Kliska, Slobodni programi d.o.o., Zagreb
        https://www.slobodni-programi.hr,
        Ivana Boras, Uvid d.o.o., Zagreb
        https://uvid.hr/

Contributions:
  Tomislav Bošnjaković, Storm Computers: tipovi konta
  Ivan Vađić, Slobodni programi: tipovi konta
  Ivana Šimek, Uvid d.o.o. : tipovi konta, porezi, fiskalna pozicija

Description:

Croatian Chart of Accounts (RRIF ver.2021)

RRIF-ov računski plan za poduzetnike za 2021.
Vrste konta
Kontni plan prema RRIF-u, dorađen u smislu kraćenja naziva i dodavanja analitika
Porezne grupe prema poreznoj prijavi
Porezi PDV obrasca
Ostali porezi
Osnovne fiskalne pozicije

Izvori podataka:
https://www.rrif.hr/dok/preuzimanje/RRIF-RP2021.PDF

""",
    "version": "15.0",
    "author": "OpenERP Croatian Community",
    'category': 'Accounting/Localizations/Account Charts',

    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_hr_chart_data.xml',
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account_chart_tag_data.xml',
        'data/account.tax.group.csv',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_tax_fiscal_position_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

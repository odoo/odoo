# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Goran Kliska
# mail:   goran.kliska(AT)slobodni-programi.hr
# Copyright (C) 2011- Slobodni programi d.o.o., Zagreb
# Contributions:
#           Tomislav Bošnjaković, Storm Computers d.o.o. :
#              - account types

{
    "name": "Croatia - Accounting (RRIF 2012)",
    "description": """
Croatian localisation.
======================

Author: Goran Kliska, Slobodni programi d.o.o., Zagreb
        https://www.slobodni-programi.hr

Contributions:
  Tomislav Bošnjaković, Storm Computers: tipovi konta
  Ivan Vađić, Slobodni programi: tipovi konta

Description:

Croatian Chart of Accounts (RRIF ver.2012)

RRIF-ov računski plan za poduzetnike za 2012.
Vrste konta
Kontni plan prema RRIF-u, dorađen u smislu kraćenja naziva i dodavanja analitika
Porezne grupe prema poreznoj prijavi
Porezi PDV obrasca
Ostali porezi
Osnovne fiskalne pozicije

Izvori podataka:
 https://www.rrif.hr/dok/preuzimanje/rrif-rp2011.rar
 https://www.rrif.hr/dok/preuzimanje/rrif-rp2012.rar

""",
    "version": "13.0",
    "author": "OpenERP Croatian Community",
    'category': 'Localization',
    "website": "https://code.launchpad.net/openobject-croatia",

    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_hr_chart_data.xml',
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account_chart_tag_data.xml',
        'data/account.tax.template.csv',
        'data/account_tax_fiscal_position_data.xml',
        'data/account_chart_template_data.yml',
    ],
    "active": False,
}

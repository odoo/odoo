# -*- coding: utf-8 -*-
# Author: Odoo House ApS <info@odoohouse.dk>

# Copyright (c) 2018 - Present | Odoo House ApS - https://odoohouse.dk
# All rights reserved.

{
    'name': 'Denmark - Accounting',
    'version': '1.0',
    'author': 'Odoo House ApS',
    'website': 'https://odoohouse.dk',
    'category': 'Localization',
    'description': """
Localization Module for Denmark
===============================
This is the module to manage the **accounting chart for Denmark**. Cover both one-man business as well as I/S, IVS, ApS and A/S

**Modulet opsætter:**

- **Dansk kontoplan**

- Dansk moms
        - 25% moms
        - Hotel moms 12,50%
        - Resturationsmoms 6,25%
        - Omvendt betalingspligt
- Konteringsgrupper
        - EU (Virksomhed)
        - EU (Privat)
        - 3.lande
- Finans raporter
        - Resulttopgørelse
        - Balance
        - Momsafregning
            - Afregning
            - Rubrik A, B og C
- **Anglo-Saxon regnskabsmetode**

Produkt setup:
==============
**Vare**
**Salgsmoms:**      Salgmoms 25%
**Salgskonto:**     1010 Salg af vare, m/moms
**Købsmoms:**       Købsmoms 25%
**Købskonto:**      2010 Direkte omkostninger vare, m/moms
.
**Ydelse**
**Salgsmoms:**      Salgmoms 25%, ydelser
**Salgskonto:**     1011 Salg af ydelser, m/moms
**Købsmoms:**       Købsmoms 25%, ydelser
**Købskonto:**      2011 Direkte omkostninger ydelser, m/moms
.
**Vare med omvendt betalingspligt**
**Salgsmoms:**      Salg omvendt betalingspligt
**Salgskonto:**     1012 Salg af vare, u/moms
**Købsmoms:**       Køb omvendt betalingspligt
**Købskonto:**      2012 Direkte omkostninger vare, u/moms
.
**Hotelophold**
**Købsmoms:**       Hotel moms 12,50%, købsmoms
**Købskonto:**      4040 Hotelophold
.
**Restauration**
**Købsmoms:**       Restaurationsmoms 6,25%, købsmoms
**Købskonto:**      4010 Restaurationsbesøg
.

Copyright 2018 Odoo House ApS
    """,
    'depends': ['account', 'base_iban', 'base_vat'],
    'data': [
        'data/account_tag_data.xml',
        'data/l10n_dk_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_dk_chart_post_data.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_data.xml',
        'data/account_chart_template_configuration_data.xml',
    ],
}

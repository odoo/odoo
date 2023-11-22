# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Denmark - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['dk'],
    'version': '1.1',
    'author': 'Odoo House ApS, VK DATA ApS',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """

Localization Module for Denmark
===============================

This is the module to manage the **accounting chart for Denmark**. Cover both one-man business as well as I/S, IVS, ApS and A/S

**Modulet opsætter:**

- **Dansk kontoplan**

- Dansk moms
        - 25% moms
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

.

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

**Restauration**

**Købsmoms:**       Restaurationsmoms 6,25%, købsmoms

**Købskonto:**      4010 Restaurationsbesøg

.

    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
    ],
    'data': [
        'data/account_account_tags.xml',
        'data/account_tax_report_data.xml',
        'data/account.account.tag.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

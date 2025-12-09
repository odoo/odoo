# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Denmark - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['dk'],
    'version': '1.3',
    'author': 'Odoo House ApS, VK DATA ApS, FlexERP ApS',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """

Localization Module for Denmark
===============================

This is the module to manage the **accounting chart for Denmark**. Cover both one-man business as well as I/S, IVS, ApS and A/S

**Modulet opsætter:**

- **Dansk kontoplan**

- Dansk moms
        - 25 % moms
        - Restaurationsmoms 6,25 %
        - Omvendt betalingspligt

- Konteringsgrupper
        - EU (Virksomhed)
        - EU (Privat)
        - Tredjelande

- Finansrapporter
        - Resultatopgørelse
        - Balance
        - Momsafregning
            - Afregning
            - Rubrik A, B og C

- **Anglo-saksisk regnskabsmetode**

.

Produktopsætning:
=================

**Vare**

**Salgsmoms:**      Salgsmoms 25 %

**Salgskonto:**     1.010 Salg af varer inkl. moms

**Købsmoms:**       Købsmoms 25 %

**Købskonto:**      2.010 Direkte vareomkostninger inkl. moms

.

**Ydelse**

**Salgsmoms:**      Salgsmoms 25 %, ydelser

**Salgskonto:**     1.011 Salg af ydelser inkl. moms

**Købsmoms:**       Købsmoms 25 %, ydelser

**Købskonto:**      2.011 Direkte omkostninger ydelser inkl. moms

.

**Vare med omvendt betalingspligt**

**Salgsmoms:**      Salg med omvendt betalingspligt

**Salgskonto:**     1.012 Salg af varer ekskl. moms

**Købsmoms:**       Køb med omvendt betalingspligt

**Købskonto:**      2.012 Direkte vareomkostninger ekskl. moms


.

**Restauration**

**Købsmoms:**       Restaurationsmoms 6,25 %, købsmoms

**Købskonto:**      4010 Restaurationsbesøg
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'data/account.account.tag.csv',
        'views/account_journal_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

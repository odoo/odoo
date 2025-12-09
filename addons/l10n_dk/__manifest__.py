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
<<<<<<< 43f7497865ee65ea4b619497c723762ee1f469fb
Also provides Nemhandel registration and invoice sending throught the Odoo Access Point

||||||| bbf3bd7b0e1d3e015350f9c959fad056384e2318

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

=======

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
>>>>>>> fb596e6882d6b9d07cab7f39702a2a5125d9935d
    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_report_data.xml',
        'data/account.account.tag.csv',
        'data/cron.xml',
        'data/nemhandel_onboarding_tour.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/nemhandel_registration_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/nemhandel_mode_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_dk/static/src/components/**/*',
            'l10n_dk/static/src/tours/nemhandel_onboarding.js',
        ],
    },
    'license': 'LGPL-3',
    'pre_init_hook': '_pre_init_nemhandel',
    'uninstall_hook': 'uninstall_hook',
}

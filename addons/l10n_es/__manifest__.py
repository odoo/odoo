# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Spain - Accounting (PGCE 2008)',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/spain.html',
    'version': '5.4',
    'icon': '/account/static/description/l10n.png',
    'countries': ['es'],
    'author': 'Spanish Localization Team',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Spanish charts of accounts (PGCE 2008).
========================================

    * Defines the following chart of account templates:
        * Spanish general chart of accounts 2008
        * Spanish general chart of accounts 2008 for small and medium companies
        * Spanish general chart of accounts 2008 for associations
    * Defines templates for sale and purchase VAT
    * Defines tax templates
    * Defines fiscal positions for spanish fiscal legislation
    * Defines tax reports mod 111, 115, 130 and 303

5.3: Update taxes starting Q4 2024 according to BOE-A-2024-12944 (Royal Decree 4/2024) https://www.boe.es/buscar/act.php?id=BOE-A-2024-12944
""",
    'depends': [
        'account',
        'base_iban',
        'base_vat',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag.csv',
        'data/res_partner_data.xml',
        'data/res_country_group.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'data/product_data.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'data/mod111.xml',
        'data/mod115.xml',
        'data/mod130.xml',
        'data/mod303.xml',
        'data/mod390/mod390_section1.xml',
        'data/mod390/mod390_section2.xml',
        'data/mod390/mod390_section3.xml',
        'data/mod390/mod390_section4.xml',
        'data/mod390/mod390_section5.xml',
        'data/mod390/mod390_section6.xml',
        'data/mod390/mod390_section7.xml',
        'data/mod390/mod390.xml',
        'data/mod420.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Accounting EDI',
    'version': '3.3',
    'description': '''
Functional
----------

This module adds accounting features for Ecuadorian localization, which
represent the minimun requirements to operate a business in Ecuador in compliance
with local regulation bodies such as the ecuadorian tax authority -SRI- and the 
Superintendency of Companies -Super Intendencia de Compañías-

Follow the next configuration steps:
1. Go to your company and configure your country as Ecuador
2. Install the invoicing or accounting module, everything will be handled automatically

Highlights:
* Ecuadorian chart of accounts will be automatically installed, based on example provided by Super Intendencia de Compañías
* List of taxes (including withholds) will also be installed, you can switch off the ones your company doesn't use
* Fiscal position, document types, list of local banks, list of local states, etc, will also be installed

Technical
---------
Master Data:
* Chart of Accounts, based on recomendation by Super Cías
* Ecuadorian Taxes, Tax Tags, and Tax Groups
* Ecuadorian Fiscal Positions
* Document types (there are about 41 purchase documents types in Ecuador)
* Identification types
* Ecuador states with its codes
* Ecuador banks
* Partners: Consumidor Final, SRI, IESS, and also basic VAT validation

Authors:
    Ing. Andres Calle <andres.calle@trescloud.com>
    Ing. José Miguel Rivero <jose.rivero@trescloud.com>
    ''',
    'author': 'OPA CONSULTING & TRESCLOUD',
    'category': 'Accounting/Localizations/Account Charts',
    'maintainer': 'OPA CONSULTING',
    'website': 'https://opa-consulting.com',
    'license': 'OEEL-1',
    'depends': [
     'l10n_ec',
    ],   
    'data': [
        'data/account_tax_group_data.xml',
        'data/account_tax_template_vat_data.xml',
        'data/account_tax_template_withhold_profit_data.xml',
        'data/account_tax_template_withhold_vat_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/l10n_latam_document_type_data.xml',
        'data/l10n.ec.sri.payment.csv',
        'views/account_tax_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/l10n_ec_sri_payment.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}

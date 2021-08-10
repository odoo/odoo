# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Accounting',
    'version': '3.3',
    'description': '''
Functional
----------

This module adds accounting features for Ecuadorian localization, which
represent the minimum requirements to operate a business in Ecuador in compliance
with local regulation bodies such as the ecuadorian tax authority -SRI- and the 
Superintendency of Companies -Super Intendencia de Compañías-

Technical
---------
Master Data:
* Chart of Accounts, IFRS (NIIFs) compatible
* Ecuadorian Taxes, Tax Tags, and Tax Groups
* Ecuadorian Fiscal Positions
* Document types (there are about 41 purchase documents types in Ecuador)
* Identification types
* Ecuador banks
* Partners: Consumidor Final, SRI, IESS, and also basic VAT validation
    ''',
    'author': 'OPA CONSULTING & TRESCLOUD',
    'category': 'Accounting/Localizations/Account Charts',
    'maintainer': 'OPA CONSULTING',
    'website': 'https://opa-consulting.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_latam_invoice_document',
        'l10n_latam_base',
    ],   
    'data': [
        #Chart of Accounts
        'data/account_chart_template_data.xml',
        'data/account_group_template_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_setup_accounts.xml',
        #Taxes
        'data/account_tax_group_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_vat_data.xml',
        #'data/account_tax_template_withhold_profit_data.xml',
        'data/account_tax_template_withhold_vat_data.xml',
        'data/account_fiscal_position_template.xml',
        
        #Partners data
        'data/res.bank.csv',
        'data/l10n_latam_identification_type_data.xml',
        'data/res_partner_data.xml',
        #Other data
        
        'data/account_chart_template_configure_data.xml',
         
        'data/l10n_latam_document_type_data.xml',
        'data/l10n.ec.sri.payment.csv',
        'views/account_tax_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/l10n_ec_sri_payment.xml',
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
        'security/ir.model.access.csv'
        
    ],
    'demo': [
        'demo/demo_company.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}

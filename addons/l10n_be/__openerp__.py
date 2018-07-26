# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Belgium in OpenERP.
==============================================================================

After installing this module, the Configuration wizard for accounting is launched.
    * We have the account templates which can be helpful to generate Charts of Accounts.
    * On that particular wizard, you will be asked to pass the name of the company,
      the chart template to follow, the no. of digits to generate, the code for your
      account and bank account, currency to create journals.

Thus, the pure copy of Chart Template is generated.

Wizards provided by this module:
--------------------------------
    * Partner VAT Intra: Enlist the partners with their related VAT and invoiced
      amounts. Prepares an XML file format.
      
        **Path to access :** Invoicing/Reporting/Legal Reports/Belgium Statements/Partner VAT Intra
    * Periodical VAT Declaration: Prepares an XML file for Vat Declaration of
      the Main company of the User currently Logged in.
      
        **Path to access :** Invoicing/Reporting/Legal Reports/Belgium Statements/Periodical VAT Declaration
    * Annual Listing Of VAT-Subjected Customers: Prepares an XML file for Vat
      Declaration of the Main company of the User currently Logged in Based on
      Fiscal year.
      
        **Path to access :** Invoicing/Reporting/Legal Reports/Belgium Statements/Annual Listing Of VAT-Subjected Customers

    """,
    'author': 'Noviat & OpenERP SA',
    'depends': [
        'account',
        'base_vat',
        'base_iban',
        'l10n_multilang',
    ],
    'data': [
        'account_chart_template.xml',
        'account_pcmn_belgium.xml',
        'account_tax_template.xml',
        'l10n_be_sequence.xml',
        'fiscal_templates.xml',
        'account_fiscal_position_tax_template.xml',
        'account_chart_template.yml',
        'security/ir.model.access.csv',
        'menuitem.xml'
    ],
    'demo': [
        'demo/l10n_be_demo.yml',
        '../account/demo/account_bank_statement.yml',
        '../account/demo/account_invoice_demo.yml',
    ],
    'test': [
    ],
    'installable': True,
    'website': 'https://www.odoo.com/page/accounting',
    'post_init_hook': 'load_translations',
}

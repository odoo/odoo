# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Belgium in Odoo.
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
    'author': 'Noviat, Odoo SA',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
        'l10n_multilang',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account_pcmn_belgium_data.xml',
        'data/account_data.xml',
        'data/account_tax_template_data.xml',
        'data/l10n_be_sequence_data.xml',
        'data/fiscal_templates_data.xml',
        'data/account_fiscal_position_tax_template_data.xml',
        'data/account_reconcile_model_template.xml',
        'data/account_chart_template_data.yml',
        'data/menuitem_data.xml',
    ],
    'demo': [
        'demo/l10n_be_demo.yml',
        '../account/demo/account_bank_statement.yml',
        '../account/demo/account_invoice_demo.yml',
    ],
    'website': 'https://www.odoo.com/page/accounting',
    'post_init_hook': 'load_translations',
}

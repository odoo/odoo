# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Main contributor: Nicolas Bessi. Camptocamp SA
# Financial contributors: Hasa SA, Open Net SA,
#                         Prisme Solutions Informatique SA, Quod SA
# Translation contributors: brain-tec AG, Agile Business Group
{
    'name': "Switzerland - Accounting",
    'description': """
Swiss localization
==================
This module defines a chart of account for Switzerland (Swiss PME/KMU 2015), taxes and enables the generation of ISR and QR-bill when you print an invoice or send it by mail.

An ISR will be generated if you specify the information it needs :
    - The bank account you expect to be paid on must be set, and have a valid postal reference.
    - Your invoice must have been set assigned a bank account to receive its payment
      (this can be done manually, but a default value is automatically set if you have defined a bank account).
    - You must have set the postal references of your bank.
    - Your invoice must be in EUR or CHF (as ISRs do not accept other currencies)

A QR-bill will be generated if:
    - The partner set on your invoice has a complete address (street, city, postal code and country) in Switzerland
    - The option to generate the Swiss QR-code is selected on the invoice (done by default)
    - A correct account number/QR IBAN is set on your bank journal
    - (when using a QR-IBAN): the payment reference of the invoice is a QR-reference

The generation of the ISR and QR-bill is automatic if you meet the previous criteria.

Here is how it works:
    - Printing the invoice will trigger the download of three files: the invoice, its ISR and its QR-bill
    - Clicking the 'Send by mail' button will attach three files to your draft mail : the invoice, the ISR and the QR-bill.
    """,
    'version': '11.0',
    'category': 'Accounting/Localizations/Account Charts',

    'depends': ['account', 'l10n_multilang', 'base_iban', 'l10n_din5008'],

    'data': [
        'security/ir.model.access.csv',
        'data/l10n_ch_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_ch_chart_post_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_vat2011_data.xml',
        'data/account_fiscal_position_data.xml',
        'data/account_chart_template_data.xml',
        'report/isr_report.xml',
        'report/swissqr_report.xml',
        'views/res_bank_view.xml',
        'views/account_invoice_view.xml',
        'views/account_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/setup_wizard_views.xml',
        'views/qr_invoice_wizard_view.xml'
    ],

    'demo': [
        'demo/account_cash_rounding.xml',
        'demo/demo_company.xml',
        'demo/res_partner_demo.xml',
    ],
    'post_init_hook': 'post_init',
    'assets': {
        'web.report_assets_common': [
            'l10n_ch/static/src/scss/**/*',
        ],
    },
    'license': 'LGPL-3',
}

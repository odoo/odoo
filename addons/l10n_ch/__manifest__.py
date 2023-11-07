# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Switzerland - Accounting',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/switzerland.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ch'],
    'description': """
Swiss localization
==================
This module defines a chart of account for Switzerland (Swiss PME/KMU 2015), taxes and enables the generation of a QR-bill when you print an invoice or send it by mail.
The QR bill is attached to the invoice and eases its payment.

A QR-bill will be generated if:
    - The partner set on your invoice has a complete address (street, city, postal code and country) in Switzerland
    - The option to generate the Swiss QR-code is selected on the invoice (done by default)
    - A correct account number/QR IBAN is set on your bank journal
    - (when using a QR-IBAN): the payment reference of the invoice is a QR-reference

The generation of the QR-bill is automatic if you meet the previous criteria. The QR-bill will be appended after the invoice when printing or sending by mail. 

    """,
    'version': '11.1',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_iban',
        'l10n_din5008',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_report_data.xml',
        'report/swissqr_report.xml',
        'views/res_bank_view.xml',
        'views/account_invoice.xml',
        'views/setup_wizard_views.xml',
        'views/qr_invoice_wizard_view.xml',
        'views/account_payment_view.xml',
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
    }
,
    'license': 'LGPL-3',
}

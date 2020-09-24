# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Sweden - Structured Communication OCR',
    'version' : '1.0',
    'author': 'XCLUDE',
    'website': 'https://www.xclude.se',
    'category': 'Accounting/Localizations',
    'description': """
Add Structured Communication to Customer Invoices and Vendor Bill.
------------------------------------------------------------------

Using OCR structured communication simplifies the reconciliation between invoices and payments.

For Customer Invoicing support for OCR level 1 to 4. The OCR number can be based on partner or
the invoice.

For Vendor Bill support, Default Vendor Specific OCR and validation for OCR are added.
    """,
    'depends': ['l10n_se'],
    'data': [
        'views/partner_view.xml',
        'views/account_journal_view.xml'
    ],
    'auto_install': True,
}

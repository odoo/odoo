# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Accounting - Cheque Management",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "Customer and supplier cheque management with cheque book and printing",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account",
        "od19_partner_thai_fields",
        "od19_accounting_features",
    ],
    "data": [
        "data/sequence.xml",
        "security/ir.model.access.csv",
        "views/account_cheque_views.xml",
        "views/account_cheque_book_views.xml",
        "views/res_company_views.xml",
        "views/account_payment_views.xml",
        "report/cheque_print_report.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_accounting_cheque/static/description/icon.svg",
}

# -*- coding: utf-8 -*-
{
    "name": "Accounting Document Sequences (OD19)",
    "version": "19.0.1.0.0",
    "summary": "Voucher, billing, WHT, VAT, bank, petty cash, asset and more sequences",
    "description": """
Pre-configured document sequences for accounting operations:
vouchers, billing, prepayments, WHT, VAT, bank vouchers, petty cash,
asset stock checking/location transfer, cheque book, cash in/out, etc.
    """,
    "author": "OD19 Custom",
    "category": "Accounting/Localizations/Account Charts",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "data/ir_sequence_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_accounting_document_sequence/static/description/icon.svg",
}

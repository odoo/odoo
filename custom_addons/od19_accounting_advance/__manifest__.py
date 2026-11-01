{
    "name": "OD19 Accounting - Advance Payment",
    "author": "OD19",
    "version": "19.0.1.1.0",
    "category": "Accounting/Payments",
    "summary": "Customer and supplier advance payment tracking "
    "(deposit VAT, security deposit, prepayment WHT)",
    "depends": [
        "account",
        "purchase_stock",
        "l10n_th_account_tax",
        "od19_accounting_features",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/account_advance_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}

{
    "name": "OD19 Accounting - Advance Payment",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "Customer and supplier advance payment tracking",
    "depends": [
        "account",
        "purchase_stock",
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

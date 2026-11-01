{
    "name": "OD19 Accounting - Petty Cash",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "Petty cash fund management with expense and replenishment tracking",
    "depends": [
        "account",
        "purchase_stock",
        "od19_accounting_features",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/petty_cash_fund_views.xml",
        "views/petty_cash_transaction_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_petty_cash/static/description/icon.svg",
}

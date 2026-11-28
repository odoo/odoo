{
    "name": "Accounting Promises",
    "summary": "Manage Customer Payment Promises",
    "description": """
    Track customer promises to pay outstanding invoices.
    """,
    "version": "19.0.1.0.0",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_payment_promise_wizard.xml",
        "views/account_move_view.xml",
        "views/res_partner_view.xml",
    ],
    "author": "Smit Patel",
    "application": False,
    "installable": True,
    "license": "LGPL-3",
}

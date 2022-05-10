{
    "name": "Asiapay Payment Acquirer",
    "category": "Accounting/Payment Acquirers",
    "version": "1.0",
    "author": "Odoo PS",
    "summary": "Payment Acquirer: Asiapay Implementation",
    "website": "https://www.odoo.com",
    "depends": ["payment"],
    "data": [
        "views/payment_views.xml",
        "views/payment_asiapay_templates.xml",
        "data/payment_acquirer_data.xml",
    ],
    "application": True,
    "uninstall_hook": "uninstall_hook",
    "license": "LGPL-3",
}

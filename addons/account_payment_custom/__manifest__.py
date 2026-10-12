# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Custom / Account Payment",
    "category": "Accounting/Payment Custom",
    "sequence": 350,
    "summary": "Bridge between payment_custom and account_payment.",
    "depends": ["account_payment", "payment_custom"],
    "data": ["data/account_payment_method.xml", "data/ir_cron.xml"],
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Payfort Payment Acquirer",
    "category": "Accounting/Payment",
    "summary": "Payment Acquirer: Payfort Implementation",
    "version": "1.0",
    "description": """Payfort Payment Acquirer""",
    "depends": ["payment"],
    "data": [
        "views/payment_views.xml",
        "views/payment_payfort_templates.xml",
        "data/payment_acquirer_data.xml",
    ],
    "installable": True,
    "post_init_hook": "create_missing_journal_for_acquirers",
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "TaxCloud and Subscriptions",
    "summary": """Compute taxes with TaxCloud after automatic invoice creation.""",
    "description": """This module ensures that the taxes are computed on the invoice before a payment is created automatically for a subscription.
    """,
    "category": 'Sales/Subscriptions',
    "depends": ["sale_subscription", "account_taxcloud"],
    "auto_install": True,
    "license": "OEEL-1",
}

# -*- coding: utf-8 -*-
{
    "name": "Live Currency Exchange Rate",
    "version": "1.0",
    "author": "Odoo S.A.",
    "category": "Financial Management/Configuration",
    "description": """Import exchange rates from the Internet.

""",
    "depends": [
        "base",
    ],
    "data": [
        "views/company_view.xml",
        "views/currency_rate_update.xml",
        "views/service_cron_data.xml",
        "security/ir.model.access.csv"
    ],
    "demo": [],
    "active": False,
    'installable': True
}

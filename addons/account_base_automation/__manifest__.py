# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Base Automation in Invoicing",
    "version": "1.0",
    "summary": "Base Automation in Invoicing",
    "description": """
Executes automated actions triggered by computed fields.
    """,
    "category": "Accounting/Accounting",
    "website": "https://www.odoo.com/page/billing",
    "depends": ["account", "base_automation"],
    "data": ["data/base_automation_data.xml",],
    "installable": True,
    "auto_install": True,
}

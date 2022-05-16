# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Indian - E-WayBill",
    "version": "1.0",
    "icon": "/l10n_in/static/description/icon.png",
    "description": """
Indian - E-Waybill
====================
To submit E-Waybill through API to the government.
We use "Tera Software Limited" as GSP

Step 1: First you need to create an API username and password in the E-Waybill portal.
Step 2: Switch to company related to that GST number
Step 3: Set that username and password in Odoo (Goto: Inventory/Configuration -> Settings -> Indian E-Waybill or find "E-Waybill" in search bar)
Step 4: Repeat steps 1,2,3 for all GSTIN you have in odoo. If you have a multi-company with the same GST number then perform step 1 for the first company only.
    """,
    "author": "Odoo",
    "website": "http://www.odoo.com",
    "category": "Accounting/Localizations/EDI",
    "depends": ["l10n_in_edi", "stock_account", "l10n_in_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "data/ewaybill_type_data.xml",
        "views/stock_picking_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/extend_or_update_part_b_wizard_views.xml",
        "report/report_deliveryslip.xml",
        "report/report_stockpicking_operations.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

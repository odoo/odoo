# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Indian - E-invoicing""",
    "version": "1.03.00",
    'countries': ['in'],
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "account_edi",
        "l10n_in",
    ],
    "description": """
Indian - E-invoicing
====================
To submit invoicing through API to the government.
We use "Tera Software Limited" as GSP

Step 1: First you need to create an API username and password in the E-invoice portal.
Step 2: Switch to company related to that GST number
Step 3: Set that username and password in Odoo (Goto: Invoicing/Accounting -> Configuration -> Settings -> Customer Invoices or find "E-invoice" in search bar)
Step 4: Repeat steps 1,2,3 for all GSTIN you have in odoo. If you have a multi-company with the same GST number then perform step 1 for the first company only.

For the creation of API username and password please ref this document: <https://service.odoo.co.in/einvoice_create_api_user>
    """,
    "data": [
        "data/account_edi_data.xml",
        "views/res_config_settings_views.xml",
        "views/edi_pdf_report.xml",
        "views/account_move_views.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}

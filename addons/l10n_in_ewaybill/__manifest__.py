{
    "name": "Indian - E-waybill",
    "version": "2.1",
    "category": "Accounting/Localizations",
    "description": """
Indian - E-waybill
====================================
To submit E-waybill through API to the government.
We use "Tera Software Limited" as GSP

Step 1: First you need to create an API username and password in the E-waybill portal.
Step 2: Switch to company related to that GST number
Step 3: Set that username and password in Odoo (Goto: Invoicing/Accounting -> Configration -> Settings -> Indian Electronic WayBill or find "E-waybill" in search bar)
Step 4: Repeat steps 1,2,3 for all GSTIN you have in odoo. If you have a multi-company with the same GST number then perform step 1 for the first company only.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "l10n_in",
    ],
    "countries": [
        "in",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "data/ewaybill_type_data.xml",
        "views/l10n_in_ewaybill_views.xml",
        "views/account_move_views.xml",
        "views/edi_pdf_report.xml",
        "views/res_config_settings_views.xml",
        "wizards/l10n_in_ewaybill_cancel_views.xml",
        "reports/ewaybill_report_views.xml",
        "reports/ewaybill_report.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
}

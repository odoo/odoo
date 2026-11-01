{
    "name": "OD19 Sales - Native Sale Order Report (QWeb)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "ใบสั่งขายรูปแบบ Odoo 19 Native (QWeb PDF) - รูปแบบดั้งเดิม และ รูปแบบปรับปรุง",
    "description": """
OD19 Sales - Native Sale Order Report (QWeb)
============================================

Ported version of the legacy Jasper form ``F-S-002`` (``dtr_sales_form``) built
with the report engine Odoo 19 supports natively (QWeb PDF).  The data shown is
the same as the Jasper original; the module ships two designs so they can be
compared side by side:

* **รูปแบบดั้งเดิม (Classic)** - reproduces the layout/data of the Jasper
  ``sale_order_form.jrxml``: company block, document info table, customer /
  invoice / delivery address blocks, line table, remark, amount block
  (Subtotal Amount / Trade Discount Amount / After Trade Amount / Untaxed
  Amount / VAT / Grand Total + amount in words) and the three signature boxes.
* **รูปแบบปรับปรุง (Modern)** - same data, redesigned for readability: brand
  colour header, KPI strip, card based sections and a highlighted total panel.

The legacy Jasper report stays available through ``od19_sale_jasper`` and keeps
its "(J-Report OD15)" label; this module only adds the native equivalents.
    """,
    "depends": [
        "sale",
        "sales_team",
        "od19_partner_thai_fields",
        "od19_thai_font_support",
    ],
    "data": [
        "report/sale_order_report.xml",
        "report/sale_order_report_variants.xml",
        "views/sale_order_report_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}

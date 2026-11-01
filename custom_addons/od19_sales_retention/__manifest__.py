{
    "name": "OD19 Sales - Retention (เงินประกันผลงาน)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "เงินประกันผลงาน (Retention) - ออกใบกำกับเต็มจำนวน "
    "แยกยอด retention ไปบัญชีลูกหนี้เงินประกัน และติดตามกำหนดคืน",
    "description": """
OD19 Sales - Retention (เงินประกันผลงาน)
========================================

กระบวนการหักเงินประกันผลงาน (Retention) สำหรับงานโครงการ/ก่อสร้าง
ตามหนังสือตอบข้อหารือ กค 0706/พ.789:

* กำหนดอัตรา/ยอด retention ต่อสัญญา/งวด (``od19_retention_rate``,
  ``od19_retention_amount``)
* ออกใบกำกับภาษี **เต็มจำนวน** เมื่อส่งมอบงวดงาน แล้วแยกยอด retention
  ไปพักไว้ที่ **บัญชีลูกหนี้เงินประกัน** เพื่อให้ VAT ขาย (ภ.พ.30) ถูกต้อง
* ติดตามกำหนดคืน (retention release) + แจ้งเตือนด้วย cron + ใบสำคัญรับ
    """,
    "depends": [
        "sale_management",
        "mail",
        "od19_sales_contract_core",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/retention_cron.xml",
        "report/sales_retention_report.xml",
        "views/sales_retention_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_sales_retention/static/description/icon.svg",
}

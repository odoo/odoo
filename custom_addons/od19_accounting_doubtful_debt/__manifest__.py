{
    "name": "OD19 Accounting - Doubtful Debt (หนี้สงสัยจะสูญ)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "ตั้งค่าเผื่อหนี้สงสัยจะสูญตามช่วง aging, ตัดหนี้สูญ "
    "พร้อมหลักฐาน/สายอนุมัติ และรายงานลูกหนี้คงค้าง/ตัดจำหน่าย",
    "description": """
OD19 Accounting - Doubtful Debt (หนี้สงสัยจะสูญ)
=================================================

กระบวนการประมาณการและตัดจำหน่ายลูกหนี้ที่สงสัยจะสูญ:

* ตั้งค่า **ช่วงอายุหนี้ (aging bucket)** และ **อัตราการตั้งเผื่อ** ต่อบริษัท
* สร้างเอกสาร **ตั้งค่าเผื่อหนี้สงสัยจะสูญ** โดยคำนวณจากลูกหนี้คงค้างจริง
  แล้วบันทึกบัญชี Dr ค่าใช้จ่ายหนี้สงสัยจะสูญ / Cr ค่าเผื่อหนี้สงสัยจะสูญ
* **ตัดหนี้สูญ** ผ่านวิซาร์ด โดยบังคับให้มี **เหตุผล + หลักฐานแนบ** และ
  **สายอนุมัติ** (เฉพาะผู้จัดการบัญชี) ก่อนตัดบัญชี
* รายงานลูกหนี้คงค้าง (aging) และใบสำคัญตัดหนี้สูญ

.. note:: เกณฑ์ทางภาษีและทางบัญชีอาจไม่ตรงกัน จึงแยกเอกสารกำกับไว้
    (อ้างอิง ประมวลรัษฎากร มาตรา 65 ทวิ (9) / ฎ.186 (2534))
    """,
    "depends": [
        "account",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "wizard/od19_writeoff_wizard_views.xml",
        "report/doubtful_debt_templates.xml",
        "report/doubtful_debt_reports.xml",
        "views/od19_doubtful_debt_aging_views.xml",
        "views/od19_doubtful_debt_provision_views.xml",
        "views/od19_doubtful_debt_writeoff_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_doubtful_debt/static/description/icon.svg",
}

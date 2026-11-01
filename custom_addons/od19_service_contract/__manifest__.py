# -*- coding: utf-8 -*-
{
    "name": "OD19 Service - Contracts (สัญญาบริการเรียกเก็บรายงวด)",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Services/After-Sales",
    "summary": "สัญญาบริการเรียกเก็บรายงวด (PM/AMC) บน OCA contract "
    "พร้อมผูกแผน PM การรับประกัน และการต่ออายุ/แจ้งเตือน",
    "description": """
OD19 Service - Contracts (สัญญาบริการเรียกเก็บรายงวด)
=====================================================

โมดูล wrapper บางที่ต่อยอด **OCA `contract`** ให้เป็น *สัญญาบริการ* สำหรับงาน
After-Sales (PM / AMC) โดยไม่แก้ไขซอร์สของ OCA (ใช้ ``_inherit`` เท่านั้น)

* เพิ่มฟิลด์บน ``contract.contract`` เพื่อระบุว่าเป็น *สัญญาบริการ* และผูกกับ
  **แผน PM (Service Card)** และ **อุปกรณ์ที่รับประกัน (Serial/Lot)**
* เรียกเก็บเงินรายงวดอัตโนมัติผ่าน cron ของ OCA ``contract`` (monthly / yearly)
* **ต่ออายุ** สัญญาได้ทั้งแบบกดเอง (``Renew Contract``) และอัตโนมัติเมื่อครบกำหนด
* **แจ้งเตือนก่อนครบกำหนด** ผ่าน ``mail.activity``

.. note:: ต้องมี submodule ``third_party/oca/contract`` (branch 19.0)
    และรวมไว้ใน ``addons_path`` ของ ``odoo.conf``
    """,
    "depends": [
        "contract",
        "od19_service_card",
        "od19_service_warranty",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/contract_views.xml",
        "views/service_card_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_service_contract/static/description/icon.svg",
}

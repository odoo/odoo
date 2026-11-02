# -*- coding: utf-8 -*-
"""s04_products — สินค้า/บริการ และหน่วยนับ"""
import common


def run(stats):
    common.log("s04_products: (scaffold) — ยังไม่ได้นำเข้าจริง")

    # TODO: อ่าน product_template/product_product จากระบบเดิม แล้ว upsert เป็น
    #   common.upsert('product.template', legacy_id, vals)
    #   - สินค้าคงคลัง: type='consu' และ is_storable=True (Odoo 17+ ใช้ is_storable)
    #   - นำเข้า default_code (รหัสสินค้า) และ barcode
    #   - map หน่วยนับผ่าน uom_map.csv -> uom_id และ uom_po_id
    #   - map หมวดหมู่สินค้า (product.category) ให้ตรงกัน ผ่าน product_category_map.csv
    #   - ตั้งบัญชีสินค้าคงคลัง/รายได้/ต้นทุน ให้ตรงกับระบบเดิม
    #     (บัญชีขึ้นกับหมวดหมู่สินค้าเป็นหลัก)
    stats.skipped += 1

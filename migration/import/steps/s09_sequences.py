# -*- coding: utf-8 -*-
"""s09_sequences — ความต่อเนื่องของเลขรัน (ir.sequence)

ตั้งเลขรันถัดไปของเอกสารแต่ละชนิดให้ต่อเนื่องจากระบบเดิม เพื่อไม่ให้เลขเอกสาร
ในระบบใหม่ชนหรือย้อนหลังกับเอกสารที่เคยออกไปแล้ว
"""
import common


def run(stats):
    common.log("s09_sequences: (scaffold) — ตั้งเลขรันถัดไปให้ต่อเนื่องจากระบบเดิม")

    # ------------------------------------------------------------------
    # TODO: อ่านเลขล่าสุดของเอกสารแต่ละชนิดจากระบบเดิม (read-only) โดยดูรหัส sequence
    #   ปลายทางจากไฟล์ sequence_map.csv (คอลัมน์ doc_type/od19_sequence_code) แล้วตั้งค่าให้
    #     seq = env['ir.sequence'].search([('code', '=', 'sale.order')], limit=1)
    #     seq.number_next_actual = last_legacy_number + 1
    #   ตรวจสอบแล้ว: ฟิลด์ number_next_actual อยู่ที่
    #     -> c:\\odoo-dev\\odoo19\\odoo\\addons\\base\\models\\ir_sequence.py:141
    #   โดย inverse _set_number_next_actual จะเขียนค่าลง number_next ให้เอง
    #     -> odoo\\addons\\base\\models\\ir_sequence.py:110
    #
    # TODO(เลขต่อแผนก): รูปแบบรหัสเอกสารซื้อ/รับเข้า เช่น WH/{DEPT}/... ต้องคง
    #   ความต่อเนื่อง "แยกตามแผนก/คลัง" ต้องตรวจว่า sequence นั้นใช้ use_date_range
    #   หรือไม่ ถ้าใช้ ให้ปรับที่ ir.sequence.date_range.number_next_actual แทน
    #     -> odoo\\addons\\base\\models\\ir_sequence.py:331
    #
    # TODO: ตรวจว่า implementation เป็น 'standard' หรือ 'no_gap' ให้ตรงนโยบายเดิม
    #   (ช่วยได้เมื่อต้องรับประกันว่าไม่ข้ามเลข)
    # ------------------------------------------------------------------

    # ตัวอย่างการใช้งาน (ยังไม่เปิดใช้): set_next_number('sale.order', 1)
    stats.skipped += 1


def set_next_number(code, next_value):
    """ตั้งเลขรันถัดไปของ ir.sequence ตาม code (คืน True ถ้าสำเร็จ).

    ใช้ฟิลด์ number_next_actual ซึ่งมี inverse เขียนลง number_next ให้อัตโนมัติ
    """
    env = common.odoo_env()
    seq = env['ir.sequence'].search([('code', '=', code)], limit=1)
    if not seq:
        common.log("คำเตือน: ไม่พบ ir.sequence ที่มี code='%s'" % code)
        return False
    seq.number_next_actual = next_value
    common.log("ตั้งเลขรัน '%s' เป็น %d เรียบร้อย" % (code, next_value))
    return True

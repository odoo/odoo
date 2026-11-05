# -*- coding: utf-8 -*-
"""ตัวรันการนำเข้าข้อมูล Odoo 15 -> Odoo 19 (เครื่องมือภายนอก ไม่ใช่โมดูล Odoo)

วิธีใช้งาน (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_pdev --no-http < migration\\import\\run.py

โหมดทดสอบ (dry-run) — ไม่เขียนข้อมูลจริง แค่ log สิ่งที่จะเขียน:

    $env:MIG_DRY_RUN = "1"
    venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_pdev --no-http < migration\\import\\run.py
    Remove-Item Env:\\MIG_DRY_RUN

หมายเหตุเรื่องการส่งอาร์กิวเมนต์:
    ภายใน `odoo shell` ไม่สามารถอ่านค่าจาก sys.argv ได้ (odoo-bin กลืน argv ไปหมด)
    จึงต้องสั่งงานผ่าน environment variable แทน:
        MIG_STEPS          รายชื่อ step คั่นด้วย comma หรือ 'all' (ค่าเริ่มต้น 'all')
        MIG_FROM           step_id ที่ต้องการเริ่มต้น (ข้าม step ก่อนหน้า)
        MIG_DRY_RUN        '1' = โหมดทดสอบ ไม่เขียนข้อมูล
        MIG_STOP_ON_ERROR  '1' = หยุดทันทีเมื่อ step ใดล้มเหลว
        MIG_IMPORT_DIR     ระบุโฟลเดอร์ migration/import เอง (ถ้าไม่รันจาก root)
"""
import os
import sys
import traceback


def _import_dir():
    """หาโฟลเดอร์ migration/import เพื่อใส่ใน sys.path (__file__ ใช้ไม่ได้ใน odoo shell)."""
    candidate = os.environ.get('MIG_IMPORT_DIR')
    if candidate and os.path.isfile(os.path.join(candidate, 'common.py')):
        return os.path.abspath(candidate)
    here = os.getcwd()
    for _ in range(6):
        guess = os.path.join(here, 'migration', 'import')
        if os.path.isfile(os.path.join(guess, 'common.py')):
            return guess
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise RuntimeError(
        "ไม่พบโฟลเดอร์ migration/import — กรุณารันจาก root ของโปรเจกต์ "
        "หรือกำหนดค่า MIG_IMPORT_DIR")


_IMPORT_DIR = _import_dir()
if _IMPORT_DIR not in sys.path:
    sys.path.insert(0, _IMPORT_DIR)

import common  # noqa: E402
from steps import (  # noqa: E402
    s01_reference,
    s02_master,
    s03_partners,
    s04_products,
    s05_terms,
    s06_people,
    s07_projects,
    s08_opening,
    s09_sequences,
    s10_attachments,
)

# ทะเบียน step ตามลำดับการโหลดที่กำหนด (ห้ามสลับลำดับ)
# รูปแบบ: (step_id, module, คำอธิบายภาษาไทย)
STEPS = (
    ('s01_reference', s01_reference, 'ข้อมูลอ้างอิง: บริษัท/สกุลเงิน/ผังบัญชี/ภาษี'),
    ('s02_master', s02_master, 'ข้อมูลหลัก: สมุดรายวัน/ภาษี/เงื่อนไขชำระ/ราคา'),
    ('s03_partners', s03_partners, 'คู่ค้า: ลูกค้า/ผู้ขาย/ผู้ติดต่อ'),
    ('s04_products', s04_products, 'สินค้า/บริการ และหน่วยนับ'),
    ('s05_terms', s05_terms, 'เงื่อนไขซื้อ/ขาย (master)'),
    ('s06_people', s06_people, 'บุคลากร: พนักงาน/แผนก/ผู้ใช้/กลุ่ม'),
    ('s07_projects', s07_projects, 'โครงการ/Job No./Analytic'),
    ('s08_opening', s08_opening, 'ยอดยกมา: AR/AP/สินค้า/สินทรัพย์/WHT/เบิกล่วงหน้า/เช็ค'),
    ('s09_sequences', s09_sequences, 'ความต่อเนื่องของเลขรัน (Sequence)'),
    ('s10_attachments', s10_attachments, 'ไฟล์แนบของข้อมูลที่ย้ายแล้ว (ir.attachment)'),
)

_ALL_IDS = [s[0] for s in STEPS]


def _selected_steps():
    """เลือก step ที่จะรันโดยพิจารณาจาก MIG_STEPS และ MIG_FROM."""
    steps_env = (os.environ.get('MIG_STEPS') or 'all').strip()
    if steps_env.lower() in ('', 'all'):
        selected = list(STEPS)
    else:
        wanted = {x.strip() for x in steps_env.split(',') if x.strip()}
        selected = [s for s in STEPS if s[0] in wanted]

    from_id = (os.environ.get('MIG_FROM') or '').strip()
    if from_id:
        if from_id not in _ALL_IDS:
            raise ValueError(
                "MIG_FROM='%s' ไม่ใช่ step ที่รู้จัก (ตัวเลือก: %s)"
                % (from_id, ', '.join(_ALL_IDS)))
        start = _ALL_IDS.index(from_id)
        selected = [s for s in selected if _ALL_IDS.index(s[0]) >= start]
    return selected


def main():
    common.init(env)  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell
    common.log("เริ่มนำเข้าข้อมูล Odoo 15 -> Odoo 19 | DRY_RUN=%s" % common.DRY_RUN)

    selected = _selected_steps()
    if not selected:
        common.log("ไม่พบขั้นตอนที่ต้องรัน (ตรวจสอบค่า MIG_STEPS/MIG_FROM)")
        return

    stop_on_error = os.environ.get('MIG_STOP_ON_ERROR', '') == '1'
    total = common.Stats()
    failed = []

    for step_id, module, desc in selected:
        common.set_step(step_id)
        common.log("=== เริ่ม %s: %s ===" % (step_id, desc))
        step_stats = common.Stats(step_id)
        try:
            module.run(step_stats)
        except Exception:
            common.log("เกิดข้อผิดพลาดใน %s:\n%s" % (step_id, traceback.format_exc()))
            env.cr.rollback()  # noqa: F821 — ย้อนข้อมูลของ step ที่ล้มเหลว
            step_stats.error += 1
            failed.append(step_id)
            if stop_on_error:
                common.log("MIG_STOP_ON_ERROR=1 — หยุดการทำงานทันที")
                break
            continue

        total.merge(step_stats)
        common.log("สรุป %s: %s" % (step_id, step_stats.summary()))

        # commit ระหว่างขั้นตอน (เฉพาะเครื่องมือภายนอกนี้เท่านั้น)
        # เหตุผล: การนำเข้าข้อมูลจริงอาจใช้เวลานานหลายชั่วโมง หากเก็บทุกขั้นตอนไว้ใน
        # transaction เดียวจะทำให้เกิด lock ค้างยาวนาน การย้อนกลับ (rollback) มีต้นทุนสูง
        # และเสี่ยงต่อฐานข้อมูลไม่ว่าง
        # จึง commit เมื่อจบแต่ละขั้นตอน เพื่อให้ทบทวนผลและรันซ้ำได้อย่างปลอดภัย
        # (ความปลอดภัยจากการรันซ้ำมาจาก External ID ของทุก record)
        env.cr.commit()  # noqa: F821

    common.set_step('')
    common.log("=== สรุปทั้งหมด: %s | ขั้นตอนที่ล้มเหลว: %s ===" % (
        total.summary(), ', '.join(failed) or 'ไม่มี'))


main()

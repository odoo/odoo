# -*- coding: utf-8 -*-
"""s09_sequences — ความต่อเนื่องของเลขรัน (ir.sequence)

ตั้งเลขรันถัดไปของเอกสารแต่ละชนิดให้ต่อเนื่องจากระบบเดิม เพื่อไม่ให้เลขเอกสาร
ในระบบใหม่ชนหรือย้อนหลังกับเอกสารที่เคยออกไปแล้ว

หลักการ:
    1. อ่าน "เลขถัดไป (effective)" ของทุก ir.sequence จากระบบเดิม (read-only)
       effective = GREATEST(ir_sequence.number_next, MAX(ir_sequence_date_range.number_next))
       — ระบบเดิมเก็บค่าจริงที่ date_range เมื่อเปิดใช้เลขแยกช่วงเวลา
    2. จับคู่ sequence ระบบเดิม -> ระบบใหม่ "ด้วย prefix" (ไม่ใช่ code)
       เพราะรหัสเอกสารปลายทางถูกแยกตามแผนก/ธนาคาร (เช่น QT → sale.quotation.ta)
       ตารางจับคู่อยู่ที่ migration/mapping/sequence_map.csv (คอลัมน์แรก = prefix ระบบเดิม)
    3. ตั้งเลขถัดไปของ sequence ปลายทาง "ไม่ให้ถอยหลัง" (ตั้งเฉพาะเมื่อค่ามากกว่าค่าปัจจุบัน)
       -> รันซ้ำได้ปลอดภัย (ไม่เปลี่ยนค่าซ้ำ)
    4. ถ้า sequence ปลายทางใช้ use_date_range ให้ปรับที่ ir.sequence.date_range
       ของช่วงเวลาปัจจุบัน (ตามความหมายของเลขต่อแผนก/ต่อช่วงเวลา)

การรันซ้ำ (idempotent): รันครั้งที่สองจะไม่มีอะไรเปลี่ยน (รายงานเป็น skipped ทั้งหมด)
"""
import common

# ไฟล์จับคู่ (คอลัมน์แรก = prefix ของ sequence ระบบเดิม)
MAP_FILE = 'sequence_map.csv'


def run(stats):
    common.log("s09_sequences: ตั้งเลขรันถัดไปให้ต่อเนื่องจากระบบเดิม")

    legacy_rows = _fetch_legacy_effective()
    mapping = common.load_map(MAP_FILE)

    changed = 0
    unchanged = 0
    skipped = 0
    unmapped = []
    seen = set()

    for row in legacy_rows:
        prefix = (row.get('prefix') or '').strip()
        eff = row.get('eff') or 0
        if eff <= 1:
            continue  # ยังไม่เคยออกเลข (ถัดไป = 1) ไม่ต้องย้าย
        if not prefix:
            skipped += 1
            unmapped.append("(ไม่มี prefix) code=%s eff=%d" % (row.get('code'), eff))
            continue

        seen.add(prefix)
        m = mapping.get(prefix)
        if not m:
            skipped += 1
            unmapped.append("(ไม่มีการจับคู่) prefix=%s eff=%d" % (prefix, eff))
            continue

        match = (m.get('od19_match') or '').strip()
        if match == 'skip':
            skipped += 1
            continue

        value = (m.get('od19_value') or '').strip()
        seq = _find_sequence(match, value)
        if not seq:
            common.log("คำเตือน: ไม่พบ ir.sequence ปลายทาง (match=%s value='%s') ของ prefix '%s'"
                       % (match, value, prefix))
            skipped += 1
            continue

        did, old, new = _set_next(seq, eff)
        if did:
            changed += 1
            stats.updated += 1
            common.log("ตั้งเลขรัน '%s' (%s): %d -> %d"
                       % (seq.code or seq.prefix or seq.name, prefix, old, new))
        else:
            unchanged += 1
            stats.skipped += 1

    stats.skipped += skipped

    # รายการที่ยังไม่มีคู่ใน OD19 (รอผู้ใช้ยืนยัน — ไม่ได้ปรับให้อัตโนมัติ)
    missing = [k for k in mapping if k not in seen and k]
    if unmapped:
        common.log("ไม่สามารถจับคู่/ข้ามไป %d รายการ:" % len(unmapped))
        for line in unmapped:
            common.log("   - %s" % line)

    common.log("สรุป s09: ปรับเลข %d / คงเดิม %d / ข้าม (ไม่มีคู่หรือ eff<=1) %d"
               % (changed, unchanged + skipped, len(missing)))
    common.log("หมายเหตุ: sequence ที่มี eff>1 แต่ 'skip' ใน sequence_map.csv "
               "ยังไม่มีคู่ใน OD19 — กรุณายืนยันก่อนปรับ (ดูคอลัมน์ note)")


# --------------------------------------------------------------------------
# การอ่านข้อมูลจากระบบเดิม
# --------------------------------------------------------------------------
def _fetch_legacy_effective():
    """อ่าน sequence ทั้งหมดของระบบเดิม พร้อมค่า effective (เลขถัดไปจริง).

    effective = GREATEST(number_next, MAX(date_range.number_next))
    """
    import legacy
    rows = legacy.fetch_all(
        """
        SELECT s.id, s.code, s.prefix, s.name, s.number_next,
               COALESCE((SELECT MAX(r.number_next)
                         FROM ir_sequence_date_range r
                         WHERE r.sequence_id = s.id), 0) AS max_range
        FROM ir_sequence s
        """)
    for r in rows:
        r['eff'] = max(r.get('number_next') or 0, r.get('max_range') or 0)
    return rows


# --------------------------------------------------------------------------
# การตั้งค่าใน Odoo 19
# --------------------------------------------------------------------------
def _find_sequence(match, value):
    """ค้นหา ir.sequence ปลายทางจาก 'code' หรือ 'prefix' (code ว่าง)."""
    env = common.odoo_env()
    Seq = env['ir.sequence']
    if match == 'code':
        return Seq.search([('code', '=', value)], limit=1)
    if match == 'prefix':
        return Seq.search([('code', '=', False), ('prefix', '=', value)], order='id', limit=1)
    common.log("คำเตือน: ค่า od19_match ไม่รู้จัก '%s'" % match)
    return Seq.browse()


def _set_next(seq, value):
    """ตั้งเลขถัดไป (ไม่ให้ถอยหลัง) คืนค่า (เปลี่ยนหรือไม่, ค่าเดิม, ค่าใหม่).

    ถ้า sequence ใช้ use_date_range จะปรับที่ date_range ของช่วงเวลาปัจจุบัน
    (ตรงกับความหมาย "เลขแยกตามช่วงเวลา/แผนก")
    """
    target = seq._get_current_sequence() if seq.use_date_range else seq
    old = target.number_next or 1
    if value <= old:
        return False, old, old
    if common.DRY_RUN:
        common.log("[DRY-RUN] จะตั้งเลขรัน '%s': %d -> %d"
                   % (seq.code or seq.prefix or seq.name, old, value))
        return True, old, value
    target.write({'number_next': value})
    return True, old, value

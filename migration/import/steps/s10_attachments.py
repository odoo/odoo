# -*- coding: utf-8 -*-
"""s10_attachments — นำเข้าไฟล์แนบ (ir.attachment) ที่ผูกกับข้อมูลซึ่งย้ายมาแล้ว

ขอบเขต (ตามที่ผู้ใช้เลือก):
    เฉพาะไฟล์แนบที่ผูกกับเรกคอร์ดที่ย้ายเข้า Odoo 19 แล้วจริง ได้แก่โมเดล
    project.project, res.partner, hr.employee, account.move, product.template
    ส่วนที่ยังไม่ได้ย้าย (เอกสารขาย/ซื้อ/สต็อก/รายงาน Jasper ฯลฯ)
    จะรอข้อมูลส่วนอื่นมาก่อน แล้วค่อยย้ายให้ครบในภายหลัง

หลักการสำคัญ:
    * ไฟล์จริงถูกคัดลอกเข้า filestore ของ Odoo 19 แล้ว
      (data_dir/filestore/<dbname>/<store_fname>) โดย store_fname ของทั้งสองระบบ
      ใช้รูปแบบเดียวกันคือ <2 ตัวอักษรแรกของ checksum>/<checksum>
    * สร้างเรกคอร์ด ir.attachment ผ่าน ORM เท่านั้น (ห้าม SQL ตรงฝั่ง Odoo 19)
      ใน Odoo 19 ฟิลด์ store_fname/checksum/file_size จะถูก "ตัดออก" ใน create()
      จึงต้องส่งเนื้อไฟล์ผ่านฟิลด์ raw เพื่อให้ Odoo คำนวณ checksum/ตำแหน่งไฟล์เอง
      (ตำแหน่งที่คำนวณได้จะตรงกับไฟล์ที่คัดลอกมาแล้ว Odoo จึงไม่เขียนไฟล์ซ้ำ)
    * res_id ต้องแมปจาก id เดิม -> id ของ Odoo 19 ผ่าน External ID
      ถ้าหาเจ้าของไฟล์ไม่พบ = ข้าม (ยังไม่ได้ย้ายข้อมูลส่วนนั้น)
    * รันซ้ำได้ (idempotent): ผูก External ID __import15__.ir_attachment.<legacy_id>
      ถ้ามีอยู่แล้วจะข้ามทันที (ไม่เขียนไฟล์ซ้ำ)

ประสิทธิภาพ (สำคัญ):
    * ปิดการทำ full-text index (index_content) ของไฟล์แนบระหว่างนำเข้า —
      ปกติ Odoo จะสกัดข้อความจาก PDF/DOCX/XLSX ด้วย pdfminer/openpyxl ทุกไฟล์
      ซึ่งช้ามากกับ PDF ใหญ่/ไฟล์ที่ stream เสียหาย (ค้างได้หลายสิบนาทีต่อไฟล์)
    * สร้างเรกคอร์ดด้วย context image_no_postprocess=True เพื่อเก็บไฟล์ต้นฉบับ
      ตามที่เป็น (ไม่ย่อ/แปลงรูปใหม่) ทำให้เนื้อไฟล์ตรงกับที่คัดลอกมาจาก Odoo 15
      และ checksum ตรงกับชื่อไฟล์เดิม Odoo จึงไม่เขียนไฟล์ซ้ำ
"""
import os

import common
import legacy

# โมเดลปลายทางที่ข้อมูลถูกย้ายมาแล้ว (ใช้กรองไฟล์แนบที่จะนำเข้าในรอบนี้)
MIGRATED_MODELS = (
    'project.project',
    'res.partner',
    'hr.employee',
    'account.move',
    'product.template',
)

# จำนวนเรกคอร์ดต่อการ commit หนึ่งครั้ง
# (ขั้นตอนนี้มีข้อมูลจำนวนมากและต้องอ่านไฟล์จริง การ commit เป็นช่วงจึงปลอดภัยกว่า)
_COMMIT_EVERY = 200


def run(stats):
    env = common.odoo_env()
    Attachment = env['ir.attachment']

    # รองรับเฉพาะที่เก็บแบบไฟล์ (filestore) — โหมด db เก็บเนื้อไฟล์ในคอลัมน์ ไม่มีไฟล์ให้คัดลอก
    if Attachment._storage() != 'file':
        raise ValueError(
            "การนำเข้าไฟล์แนบรองรับเฉพาะที่เก็บแบบไฟล์ (filestore) "
            "แต่ระบบตั้งค่า ir_attachment.location = '%s'" % Attachment._storage())

    filestore = Attachment._filestore()
    if not os.path.isdir(filestore):
        raise ValueError("ไม่พบโฟลเดอร์ filestore: %s" % filestore)
    common.log("filestore ปลายทาง: %s" % filestore)

    rows = _fetch_attachments()
    common.log("พบไฟล์แนบเป้าหมาย %d รายการ (เฉพาะที่เก็บอยู่บนดิสก์)" % len(rows))

    # ปิดการทำ full-text index ชั่วคราวระหว่างนำเข้า (เหตุผลอยู่ใน _suspend_indexation)
    index_guard = _suspend_indexation()
    try:
        processed = 0
        for row in rows:
            res_id = _owner_id(env, row['res_model'], row['res_id'])
            if not res_id:
                # เจ้าของไฟล์ยังไม่ได้ย้ายเข้า Odoo 19 — ข้ามไว้ก่อน
                stats.skipped += 1
                continue

            action = _upsert_attachment(env, filestore, row, res_id, stats)
            if action:
                stats.bump(action)

            processed += 1
            if processed % _COMMIT_EVERY == 0:
                env.cr.commit()
                common.log("... นำเข้าแล้ว %d/%d รายการ | %s"
                           % (processed, len(rows), stats.summary()))

        env.cr.commit()
    finally:
        _resume_indexation(index_guard)


# --------------------------------------------------------------------------
# การปิด/คืนการทำ full-text index ของไฟล์แนบ (เพื่อความเร็ว)
# --------------------------------------------------------------------------
def _suspend_indexation():
    """ปิดการทำ full-text index ของไฟล์แนบชั่วคราว แล้วคืนค่าเดิมเมื่อจบ

    เหตุผล: โมดูล attachment_indexation จะสกัดข้อความจาก PDF/DOCX/XLSX
    (ผ่าน pdfminer/openpyxl) เพื่อเก็บใน index_content ทุกครั้งที่สร้างไฟล์แนบ
    ซึ่งช้ามากกับ PDF ขนาดใหญ่หรือไฟล์ที่ stream เสียหาย
    (pdfminer จะสแกนแบบ exhaustive จนค้างได้หลายสิบนาทีต่อไฟล์)
    ไฟล์แนบชุดนี้มี PDF มากกว่า 4,600 ไฟล์ จึงเป็นคอขวดหลัก
    และไม่จำเป็นต่อการย้ายข้อมูลเชิงประวัติศาสตร์
    (ถ้าต้องการค้นหาข้อความในไฟล์แนบภายหลัง สามารถทำ index ใหม่ได้)
    """
    try:
        from odoo.addons.attachment_indexation.models import ir_attachment as _ai
    except ImportError:
        return None
    saved = _ai.FTYPES
    _ai.FTYPES = []
    return (_ai, saved)


def _resume_indexation(guard):
    if guard:
        module, saved = guard
        module.FTYPES = saved


# --------------------------------------------------------------------------
# การอ่านข้อมูลจากระบบเดิม / การอ้างอิงเจ้าของไฟล์
# --------------------------------------------------------------------------
def _fetch_attachments():
    """อ่านไฟล์แนบเป้าหมายจากฐานข้อมูลเดิม (เฉพาะที่เก็บไฟล์อยู่บนดิสก์)."""
    sql = (
        "SELECT id, name, description, res_model, res_field, res_id, "
        "       mimetype, store_fname, public, access_token "
        "FROM ir_attachment "
        "WHERE res_model IN %(models)s "
        "  AND type = 'binary' "
        "  AND store_fname IS NOT NULL "
        "  AND res_id IS NOT NULL "
        "ORDER BY id"
    )
    return legacy.fetch_all(sql, {'models': tuple(MIGRATED_MODELS)})


def _owner_id(env, res_model, legacy_id):
    """แปลง id เดิมของเจ้าของไฟล์ -> id ของ Odoo 19 ผ่าน External ID."""
    xmlid = common.get_xmlid(res_model, legacy_id)
    return env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)


def _upsert_attachment(env, filestore, row, res_id, stats):
    """สร้างเรกคอร์ด ir.attachment (คืนค่า 'created'/'skipped' หรือ None เมื่อข้าม)."""
    xmlid = common.get_xmlid('ir.attachment', row['id'])
    if common.DRY_RUN:
        common.log('[DRY-RUN] จะสร้าง ir.attachment %s (%s,%s) "%s"'
                   % (xmlid, row['res_model'], res_id, row['name']))
        return 'skipped'

    imd = env['ir.model.data']
    if imd._xmlid_to_res_id(xmlid, raise_if_not_found=False):
        # มีอยู่แล้ว — ไม่เขียนไฟล์ซ้ำ (เนื้อไฟล์แนบไม่มีการแก้ไข)
        return 'skipped'

    full_path = os.path.join(filestore, *row['store_fname'].split('/'))
    if not os.path.isfile(full_path):
        common.log("คำเตือน: ไม่พบไฟล์ %s ของไฟล์แนบเดิม id=%s — ข้าม"
                   % (row['store_fname'], row['id']))
        stats.error += 1
        return None

    with open(full_path, 'rb') as fh:
        raw = fh.read()

    vals = {
        'name': (row['name'] or '').strip() or 'ไฟล์แนบ %s' % row['id'],
        'description': row['description'] or False,
        'res_model': row['res_model'],
        'res_id': res_id,
        'type': 'binary',
        'public': bool(row['public']),
        # ส่งเนื้อไฟล์ผ่าน raw เพื่อให้ Odoo คำนวณ checksum/ตำแหน่งไฟล์เอง
        # (create() ของ Odoo 19 จะตัด store_fname/checksum/file_size ออกเสมอ)
        'raw': raw,
    }
    # ไฟล์ที่ผูกกับฟิลด์ (เช่น รูปพนักงาน/โลโก้คู่ค้า/ลายเซ็น) ต้องคง res_field ไว้
    if row['res_field']:
        vals['res_field'] = row['res_field']
    # คง mimetype เดิมไว้เป็นค่าตั้งต้น (_check_contents จะคำนวณใหม่ให้เอง)
    if row['mimetype']:
        vals['mimetype'] = row['mimetype']
    # คงโทเคนเดิมไว้เพื่อไม่ให้ลิงก์สำหรับผู้ใช้ภายนอกที่เคยแชร์ไว้เสีย
    if row['access_token']:
        vals['access_token'] = row['access_token']

    try:
        # ใช้ savepoint เพื่อให้เรกคอร์ดที่ล้มเหลวเพียงใบเดียวไม่ทำให้ทั้งขั้นตอนพัง
        # (image_no_postprocess = เก็บไฟล์ต้นฉบับตามจริง ไม่ย่อ/แปลงรูปใหม่)
        with env.cr.savepoint():
            rec = env['ir.attachment'].with_context(
                image_no_postprocess=True).create(vals)
            imd._update_xmlids(
                [{'xml_id': xmlid, 'record': rec, 'noupdate': True}], update=True)
    except Exception as exc:  # noqa: BLE001 — ต้องการข้ามใบที่ผิดและไปต่อ
        common.log("คำเตือน: นำเข้าไฟล์แนบเดิม id=%s (%s,%s) ไม่สำเร็จ — %s"
                   % (row['id'], row['res_model'], res_id, exc))
        stats.error += 1
        return None
    return 'created'

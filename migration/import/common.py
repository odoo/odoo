# -*- coding: utf-8 -*-
"""ตัวช่วยฝั่ง Odoo 19 — ทำงานอยู่ภายใน `odoo shell` (มีตัวแปร env อยู่แล้ว)

หลักการสำคัญ:
    * การเขียนข้อมูลลงฐานข้อมูล Odoo 19 ต้องผ่าน ORM เท่านั้น ห้ามใช้ SQL ตรง
    * ทุก record ที่นำเข้าจะต้องมี External ID รูปแบบ
      __import15__.<model_name_with_underscores>.<legacy_id>
      เพื่อให้รันซ้ำได้ (idempotent) โดยไม่เกิดข้อมูลซ้ำ
    * คอมเมนต์/ข้อความ log ทั้งหมดเป็นภาษาไทย
"""
import os
import re
import sys
import csv
import hashlib
import datetime
import logging

_logger = logging.getLogger('migration.common')

# คำนำหน้า External ID ของการนำเข้า (module ปลอมสำหรับ tooling นี้)
MODULE_PREFIX = '__import15__'

# โฟลเดอร์เก็บไฟล์ mapping CSV (migration/mapping)
MAPPING_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mapping')

# โหมดทดสอบ: เปิดเมื่อ MIG_DRY_RUN=1 (จะไม่เขียนข้อมูลจริง)
DRY_RUN = os.environ.get('MIG_DRY_RUN', '') == '1'

# ขั้นตอนปัจจุบัน (ใช้ประกอบข้อความ log)
_STEP = ''
_ENV = None


# --------------------------------------------------------------------------
# การผูก env ของ Odoo
# --------------------------------------------------------------------------
def init(env):
    """ผูก env ของ Odoo เข้ากับโมดูลนี้ (เรียกครั้งแรกใน run.py)."""
    global _ENV
    _ENV = env


def odoo_env():
    """คืนค่า env ของ Odoo 19

    ลำดับการค้นหา: ค่าที่ผูกผ่าน init() -> __main__.env -> search frame
    เพื่อรองรับทั้งการรันผ่าน run.py และการเรียกใช้ใน odoo shell โดยตรง
    """
    if _ENV is not None:
        return _ENV
    main = sys.modules.get('__main__')
    if main is not None and getattr(main, 'env', None) is not None:
        return main.env
    frame = sys._getframe(1)
    while frame is not None:
        if 'env' in frame.f_globals:
            return frame.f_globals['env']
        frame = frame.f_back
    raise RuntimeError(
        "ไม่พบตัวแปร env — กรุณารันสคริปต์นี้ภายใน `odoo shell` "
        "หรือเรียก common.init(env) ก่อนใช้งาน")


# --------------------------------------------------------------------------
# การบันทึก log และตัวนับสถิติ
# --------------------------------------------------------------------------
def set_step(step_id):
    """กำหนดชื่อขั้นตอนปัจจุบันสำหรับข้อความ log."""
    global _STEP
    _STEP = step_id or ''


def log(msg):
    """เขียนข้อความ log พร้อม prefix ขั้นตอนและเวลาปัจจุบัน."""
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = '[%s]' % _STEP if _STEP else '[mig]'
    line = '%s %s %s' % (prefix, ts, msg)
    print(line)
    _logger.info(line)


class Stats:
    """ตัวนับสถิติของแต่ละขั้นตอน (created/updated/skipped/error)."""

    def __init__(self, label=''):
        self.label = label
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.error = 0

    def bump(self, action):
        """เพิ่มตัวนับตามผลลัพธ์ที่ได้จาก upsert ('created'/'updated'/อื่น ๆ)."""
        if action == 'created':
            self.created += 1
        elif action == 'updated':
            self.updated += 1
        else:
            self.skipped += 1

    def merge(self, other):
        self.created += other.created
        self.updated += other.updated
        self.skipped += other.skipped
        self.error += other.error

    def summary(self):
        return 'created=%d updated=%d skipped=%d error=%d' % (
            self.created, self.updated, self.skipped, self.error)


# --------------------------------------------------------------------------
# External ID / upsert
# --------------------------------------------------------------------------
# ฟิลด์ name ของ ir.model.data ห้ามมีช่องว่าง/อักขระพิเศษ
_SAFE_ID = re.compile(r'^[0-9A-Za-z_]+$')
_SLUG = re.compile(r'[^0-9A-Za-z_]+')


def get_xmlid(model, legacy_id):
    """สร้าง External ID รูปแบบ __import15__.<model>.<legacy_id>.

    ค่าอ้างอิงของเดิมที่เป็นตัวเลข/ตัวอักษรล้วนจะคงรูปเดิมไว้ (เพื่อความเข้ากันได้
    กับข้อมูลที่นำเข้าไปแล้ว) ส่วนค่าที่มีช่องว่าง/อักขระพิเศษจะถูกแปลงเป็น slug
    แล้วต่อท้ายด้วย hash สั้น ๆ เพื่อกันการชนกัน (เช่น m² กับ m³)
    """
    key = str(legacy_id)
    if not _SAFE_ID.match(key):
        digest = hashlib.md5(key.encode('utf-8')).hexdigest()[:8]
        slug = _SLUG.sub('_', key).strip('_') or 'x'
        key = '%s_%s' % (slug, digest)
    return '%s.%s.%s' % (MODULE_PREFIX, model.replace('.', '_'), key)


def _changed_values(model, rec, vals):
    """เทียบหาฟิลด์ที่มีการเปลี่ยนแปลงจริง (ไม่เทียบ x2many)."""
    changed = {}
    for name, value in vals.items():
        field = model._fields.get(name)
        if field is None:
            continue
        if field.type in ('one2many', 'many2many'):
            # ปล่อยให้ผู้เรียกจัดการ x2many เอง (ซับซ้อนกว่า field เดียว)
            continue
        current = rec[name]
        if field.type == 'many2one':
            current = current.id or False
            value = value or False
        elif field.type in ('char', 'text'):
            current = current or False
            value = value or False
        if current != value:
            changed[name] = value
    return changed


def upsert(model, legacy_id, vals, context=None):
    """สร้างหรืออัปเดต record โดยอ้างอิง External ID (รันซ้ำได้ไม่เกิดข้อมูลซ้ำ)

    คืนค่า (record, action) โดย action เป็น 'created' หรือ 'updated'
    ในโหมด dry-run จะไม่เขียนข้อมูล และคืนค่า (None, 'skipped')
    context: dict ของ context เพิ่มเติม เช่น {'no_vat_validation': True}
    """
    xmlid = get_xmlid(model, legacy_id)
    if DRY_RUN:
        log('[DRY-RUN] จะ upsert %s (%s) ฟิลด์=%s' % (xmlid, model, sorted(vals)))
        return None, 'skipped'

    env = odoo_env()
    imd = env['ir.model.data']
    Model = env[model]
    if context:
        Model = Model.with_context(**context)

    existing_id = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if existing_id:
        rec = Model.browse(existing_id)
        if rec._name != model:
            raise ValueError(
                "External ID %s ชี้ไปที่โมเดล %s ไม่ใช่ %s" % (xmlid, rec._name, model))
        changed = _changed_values(Model, rec, vals)
        if changed:
            rec.write(changed)
        return rec, 'updated'

    rec = Model.create(vals)
    # ผูก External ID แบบ noupdate=True เพื่อไม่ให้ถูกเขียนทับตอนอัปเกรดโมดูล
    imd._update_xmlids(
        [{'xml_id': xmlid, 'record': rec, 'noupdate': True}],
        update=True,
    )
    return rec, 'created'


# --------------------------------------------------------------------------
# ไฟล์ mapping CSV
# --------------------------------------------------------------------------
def load_map(filename):
    """อ่านไฟล์ mapping CSV จาก migration/mapping/<filename>

    คืนค่า dict ที่ใช้คอลัมน์แรกเป็น key และเก็บแถวทั้งหมดเป็น dict
    แถวตัวอย่างที่ขึ้นต้นด้วย EXAMPLE จะถูกข้าม
    """
    path = os.path.join(MAPPING_DIR, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "ไม่พบไฟล์ mapping ที่ต้องการ: %s\n"
            "กรุณาสร้าง/แก้ไขไฟล์นี้ (ดูตัวอย่างใน migration/mapping) ก่อนรัน migration" % path)

    result = {}
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("ไฟล์ mapping ว่างหรือไม่มีบรรทัดหัวตาราง: %s" % path)
        key_field = reader.fieldnames[0]
        for row in reader:
            key = (row.get(key_field) or '').strip()
            if not key or key.upper().startswith('EXAMPLE'):
                continue  # ข้ามแถวตัวอย่าง
            cleaned = {(k or '').strip(): (v or '').strip() for k, v in row.items()}
            result[key] = cleaned
    return result


def map_required(mapping, key, label):
    """คืนค่าแถว mapping ที่ต้องการ หรือ raise ข้อความไทยที่ชัดเจนหากไม่มี."""
    row = mapping.get(key)
    if not row:
        raise KeyError(
            "ไม่พบการจับคู่ %s สำหรับค่า '%s' — กรุณาเพิ่มแถวในไฟล์ mapping ก่อนรัน migration"
            % (label, key))
    return row

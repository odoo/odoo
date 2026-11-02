# -*- coding: utf-8 -*-
"""s07_projects — โครงการ / Job No. / Analytic Account

แหล่งข้อมูลเดิม (Odoo 15): ตาราง project_project (โมเดลมาตรฐานที่ระบบเดิมต่อเติม
ฟิลด์เฉพาะ เช่น job_no / job_type / ผู้รับผิดชอบ / เอกสารที่ต้องเตรียม)

การแปลงข้อมูลหลัก:
    name                   -> name
    partner_id             -> partner_id                 (map จาก s03_partners)
    project_department_id  -> od19_department_id         (map จาก s06_people)
    user_id                -> user_id                    (ผู้จัดการโครงการ)
    job_type               -> od19_project_type          (job/pm/service/sale)
    sale_person_id         -> od19_sale_person_id        (map จาก s06_people)
    job_no                 -> job_no                     (ดูข้อตกลงด้านล่าง)
    responsible_person1/2/3-> od19_responsible_person_ids (Many2many hr.employee)
    autoinfo_coordinator   -> od19_coordinator_ids        (Many2many hr.employee)
    scope_of_work          -> od19_scope_of_work
    flag เอกสารต่าง ๆ        -> od19_document_requirements (รวมเป็นข้อความ)

การจัดการ Job No. (ตามข้อตกลงกับผู้ใช้):
    * เลขงานที่ซ้ำกับรายการอื่น: คงรายการแรกไว้ แล้วเติม -2, -3, ... ให้รายการถัดไป
      (ไม่มีข้อมูลสูญหาย และไม่ชนกับเลขงานอื่นที่มีอยู่)
    * โครงการที่ไม่มีเลขงานจากระบบเดิม: ปล่อยว่างไว้เพื่อออกเลขภายหลัง

หมายเหตุ Odoo 19:
    * project.project ที่ติดตั้ง od19_project_analytic / od19_project_document_sequence
      จะสร้างบัญชีวิเคราะห์ (account.analytic.account) ให้อัตโนมัติเมื่อไม่มี account_id
    * create() ของ od19_project_document_sequence จะ "ปฏิเสธ" โครงการชนิด sale ที่ไม่มี
      เลขงานและไม่มี sequence ของผู้ขาย จึงต้องสร้างเป็นชนิดอื่นก่อนแล้วเขียนทับ (ดู _create_project)

การรันซ้ำ (idempotent): ผูก External ID __import15__.project_project.<legacy_id>
"""
import common

# ความยาวสูงสุดของชื่อโครงการ
_NAME_MAX = 250

# ชนิดโครงการที่ยอมรับได้ (ตรงกับ od19_project_type)
_PROJECT_TYPES = {'job', 'pm', 'service', 'sale'}

# (คอลัมน์เดิม, ป้ายชื่อไทย) ของเอกสารที่ต้องเตรียม — นำเข้าเมื่อค่าตรงกับ True
_DOC_FLAGS = (
    ('document_required_entry_to_work', 'เอกสารขออนุญาตเข้าพื้นที่/เข้าทำงาน (Entry to Work)'),
    ('maintenance_wo', 'ใบสั่งงานซ่อมบำรุง (Maintenance WO)'),
    ('jsa', 'ประเมินความเสี่ยงหน้างาน (JSA)'),
    ('copy_id_card', 'สำเนาบัตรประชาชน'),
    ('copy_social_security', 'สำเนาเลขประกันสังคม'),
    ('medeical_certificate', 'ใบรับรองแพทย์'),
    ('service_report', 'รายงานการให้บริการ (Service Report)'),
    ('work_delivery', 'เอกสารส่งมอบงาน (Work Delivery)'),
    ('list_of_trainees', 'รายชื่อผู้เข้ารับการอบรม'),
    ('temporary_delivery', 'การส่งมอบชั่วคราว'),
    ('tor', 'ขอบเขตงาน/ข้อกำหนดโครงการ (TOR)'),
    ('unprice', 'เอกสารไม่แสดงราคา (Unprice)'),
)

# (คอลัมน์ flag, คอลัมน์คำอธิบาย, ป้ายชื่อไทย) — นำเข้าเมื่อ flag ตรงกับ True
_DOC_OTHER_FLAGS = (
    ('document_required_entry_to_work_other',
     'document_required_entry_to_work_other_description',
     'เอกสารอื่น ๆ ก่อนเข้าพื้นที่'),
    ('document_required_after_entering_other',
     'document_required_after_entering_other_description',
     'เอกสารอื่น ๆ หลังเข้าพื้นที่'),
    ('attachment_other', 'attachment_other_description', 'เอกสารแนบอื่น ๆ'),
    ('has_spare_part', 'spare_part', 'อะไหล่ที่ต้องเตรียม'),
)

# cache การแปลง legacy id -> id ของ Odoo 19 (ผ่าน External ID)
_RESOLVE_CACHE = {}


# --------------------------------------------------------------------------
# ตัวช่วยทั่วไป
# --------------------------------------------------------------------------
def _legacy_columns(table):
    """อ่านรายชื่อคอลัมน์จริงของตารางในระบบเดิม."""
    import legacy
    rows = legacy.fetch_all(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,))
    return {r['column_name'] for r in rows}


def _text(raw):
    """แปลงค่าเป็นข้อความล้วน (คืนค่า False เมื่อว่าง)."""
    value = raw.strip() if isinstance(raw, str) else raw
    return value or False


def _resolve(model, legacy_id):
    """คืนค่า id ใน Odoo 19 ของ record ที่นำเข้าไปก่อนหน้า (อ้าง External ID).

    คืนค่า None เมื่อไม่พบ (เช่น คู่ค้าที่ไม่ได้อยู่ในขอบเขตของ s03_partners)
    """
    if not legacy_id:
        return None
    key = (model, legacy_id)
    if key in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[key]
    env = common.odoo_env()
    xmlid = common.get_xmlid(model, legacy_id)
    res = env['ir.model.data']._xmlid_to_res_id(
        xmlid, raise_if_not_found=False) or None
    _RESOLVE_CACHE[key] = res
    return res


def _company_id(legacy_id):
    """คืนค่า company_id ที่มีจริงใน Odoo 19 (fallback = บริษัทปัจจุบัน)."""
    env = common.odoo_env()
    if legacy_id and env['res.company'].browse(legacy_id).exists():
        return legacy_id
    return env.company.id


# --------------------------------------------------------------------------
# การอ่านข้อมูลจากระบบเดิม
# --------------------------------------------------------------------------
def _fetch_projects():
    """อ่านโครงการทั้งหมดจากระบบเดิม (รวมรายการที่เก็บถาวร)."""
    import legacy
    cols = _legacy_columns('project_project')
    wanted = [
        'id', 'name', 'description', 'active', 'partner_id', 'company_id',
        'user_id', 'date_start', 'date', 'job_no', 'job_type',
        'project_department_id', 'sale_person_id',
        'responsible_person1', 'responsible_person2', 'responsible_person3',
        'autoinfo_coordinator', 'scope_of_work',
    ]
    wanted += [col for col, _label in _DOC_FLAGS]
    for flag, desc, _label in _DOC_OTHER_FLAGS:
        wanted += [flag, desc]
    use = [c for c in wanted if c in cols]
    return legacy.fetch_all(
        "SELECT %s FROM project_project ORDER BY id" % ', '.join(use))


def _assign_job_numbers(rows):
    """คำนวณเลขงานสุดท้ายของแต่ละโครงการ (คงเดิม / เติม -2,-3 / เว้นว่าง)."""
    used = set()
    for row in rows:
        job_no = _text(row.get('job_no'))
        if job_no:
            used.add(job_no)

    assigned = {}
    next_index = {}
    for row in rows:
        job_no = _text(row.get('job_no'))
        if not job_no:
            assigned[row['id']] = False
            continue
        if job_no not in next_index:
            # รายการแรกของเลขงานนี้ — คงค่าเดิมไว้
            next_index[job_no] = 1
            assigned[row['id']] = job_no
            continue
        # เลขงานซ้ำ — เติม -2, -3, ... โดยไม่ชนกับเลขงานอื่นที่มีอยู่
        index = next_index[job_no] + 1
        candidate = '%s-%d' % (job_no, index)
        while candidate in used:
            index += 1
            candidate = '%s-%d' % (job_no, index)
        next_index[job_no] = index
        used.add(candidate)
        assigned[row['id']] = candidate
    return assigned


def _document_requirements(row):
    """ประกอบข้อความ 'เอกสารที่ต้องเตรียม' จาก flag ของระบบเดิม (คืนค่า False ถ้าว่าง)."""
    lines = []
    for col, label in _DOC_FLAGS:
        if row.get(col):
            lines.append('- %s' % label)
    for flag, desc_col, label in _DOC_OTHER_FLAGS:
        if row.get(flag):
            desc = _text(row.get(desc_col))
            lines.append('- %s%s' % (label, (': %s' % desc) if desc else ''))
    return '\n'.join(lines) or False


# --------------------------------------------------------------------------
# การเขียนข้อมูลลง Odoo 19
# --------------------------------------------------------------------------
def _apply_m2m(rec, values):
    """ตั้งค่า Many2many แบบ idempotent (เทียบของเดิมก่อนเขียน)."""
    if not rec or common.DRY_RUN:
        return
    from odoo import Command
    for field, ids in values.items():
        wanted = set(ids)
        if set(rec[field].ids) != wanted:
            rec.write({field: [Command.set(sorted(wanted))]})


def _create_project(legacy_id, vals):
    """สร้างโครงการใหม่ พร้อมรองรับกรณี 'sale' ที่ยังไม่มีเลขงาน.

    create() ของ od19_project_document_sequence จะปฏิเสธโครงการชนิด 'sale'
    ที่ไม่มีเลขงานและไม่มี sequence ของผู้ขาย ตามข้อตกลงเราปล่อยเลขงานว่างไว้
    จึงสร้างเป็นชนิด 'job' ก่อน แล้วเขียนชนิดจริงทับภายหลัง
    (write() จะไม่สร้างเลขงานให้ เพราะยังไม่มี sequence ตั้งไว้ที่แผนก/ผู้ขาย)
    """
    deferred_type = None
    if not vals.get('job_no') and vals.get('od19_project_type') == 'sale':
        deferred_type = 'sale'
        vals = dict(vals, od19_project_type='job')

    rec, action = common.upsert('project.project', legacy_id, vals)
    if deferred_type and rec:
        rec.write({'od19_project_type': deferred_type})
    return rec, action


def _upsert_project(legacy_id, vals, m2m):
    """upsert โครงการ + ตั้งค่า Many2many แบบ idempotent."""
    env = common.odoo_env()
    xmlid = common.get_xmlid('project.project', legacy_id)
    existing = env['ir.model.data']._xmlid_to_res_id(
        xmlid, raise_if_not_found=False)

    if existing or common.DRY_RUN:
        rec, action = common.upsert('project.project', legacy_id, vals)
    else:
        rec, action = _create_project(legacy_id, vals)

    _apply_m2m(rec, m2m)
    return rec, action


def _sync_projects(stats):
    """นำเข้า project.project ทั้งหมด (รวมรายการที่เก็บถาวร)."""
    rows = _fetch_projects()
    job_numbers = _assign_job_numbers(rows)
    blanks = sum(1 for v in job_numbers.values() if not v)
    suffixed = sum(1 for r in rows
                   if job_numbers.get(r['id']) and job_numbers[r['id']] != _text(r.get('job_no')))
    common.log("โครงการ: พบ %d รายการ | เลขงานว่าง %d | เลขงานที่ต้องเติมท้าย %d"
               % (len(rows), blanks, suffixed))

    env = common.odoo_env()
    field_names = env['project.project']._fields
    missing = [f for f in ('od19_department_id', 'od19_project_type',
                           'od19_sale_person_id', 'od19_responsible_person_ids',
                           'od19_coordinator_ids', 'od19_scope_of_work',
                           'od19_document_requirements') if f not in field_names]
    if missing:
        common.log("คำเตือน: ไม่พบฟิลด์เป้าหมาย %s — จะข้ามฟิลด์เหล่านี้"
                   % ', '.join(missing))

    unresolved = {'partner': 0, 'dept': 0, 'user': 0, 'sale_person': 0, 'employee': 0}

    for row in rows:
        name = _text(row.get('name'))
        if not name:
            common.log("ข้ามโครงการ legacy id=%s เพราะไม่มีชื่อ" % row['id'])
            stats.skipped += 1
            continue

        vals = {
            'name': name[:_NAME_MAX],
            'active': bool(row.get('active')),
            'job_no': job_numbers.get(row['id']) or False,
            'company_id': _company_id(row.get('company_id')),
        }

        project_type = _text(row.get('job_type'))
        vals['od19_project_type'] = project_type if project_type in _PROJECT_TYPES else 'job'

        if 'od19_department_id' in field_names:
            dept = _resolve('hr.department', row.get('project_department_id'))
            if dept:
                vals['od19_department_id'] = dept
            elif row.get('project_department_id'):
                unresolved['dept'] += 1

        if row.get('partner_id'):
            partner = _resolve('res.partner', row.get('partner_id'))
            if partner:
                vals['partner_id'] = partner
            else:
                unresolved['partner'] += 1

        if row.get('user_id'):
            user = _resolve('res.users', row.get('user_id'))
            if user:
                vals['user_id'] = user
            else:
                unresolved['user'] += 1

        if 'od19_sale_person_id' in field_names and row.get('sale_person_id'):
            sale_person = _resolve('res.users', row.get('sale_person_id'))
            if sale_person:
                vals['od19_sale_person_id'] = sale_person
            else:
                unresolved['sale_person'] += 1

        description = _text(row.get('description'))
        if description:
            vals['description'] = description
        if row.get('date_start'):
            vals['date_start'] = row['date_start']
        if row.get('date'):
            vals['date'] = row['date']

        scope = _text(row.get('scope_of_work'))
        if scope and 'od19_scope_of_work' in field_names:
            vals['od19_scope_of_work'] = scope
        doc_req = _document_requirements(row)
        if doc_req and 'od19_document_requirements' in field_names:
            vals['od19_document_requirements'] = doc_req

        m2m = {}
        if 'od19_responsible_person_ids' in field_names:
            responsible = []
            for col in ('responsible_person1', 'responsible_person2',
                        'responsible_person3'):
                if not row.get(col):
                    continue
                emp = _resolve('hr.employee', row.get(col))
                if emp and emp not in responsible:
                    responsible.append(emp)
                elif not emp:
                    unresolved['employee'] += 1
            if responsible:
                m2m['od19_responsible_person_ids'] = responsible

        if 'od19_coordinator_ids' in field_names and row.get('autoinfo_coordinator'):
            coord = _resolve('hr.employee', row.get('autoinfo_coordinator'))
            if coord:
                m2m['od19_coordinator_ids'] = [coord]
            else:
                unresolved['employee'] += 1

        try:
            with env.cr.savepoint():
                _rec, action = _upsert_project(row['id'], vals, m2m)
                stats.bump(action)
        except Exception as exc:  # noqa: BLE001 — เก็บ error ต่อรายการไว้ตรวจสอบ
            stats.error += 1
            common.log("ผิดพลาด: โครงการ legacy id=%s (%s): %s"
                       % (row['id'], name[:60], exc))

    if any(unresolved.values()):
        common.log("อ้างอิงที่หาไม่พบ (ข้ามไป): %s"
                   % ', '.join('%s=%d' % kv for kv in unresolved.items() if kv[1]))
    common.log("โครงการ: นำเข้าเสร็จ %d รายการ" % len(rows))


# --------------------------------------------------------------------------
# จุดเริ่มต้นของ step
# --------------------------------------------------------------------------
def run(stats):
    _RESOLVE_CACHE.clear()
    common.log("s07_projects: เริ่มนำเข้าโครงการ (project.project)")
    _sync_projects(stats)
    common.log("s07_projects: เสร็จสิ้น")

# -*- coding: utf-8 -*-
"""s06_people — บุคลากร: แผนก / ตำแหน่งงาน / ผู้ใช้ / พนักงาน

ลำดับการนำเข้า (ห้ามสลับ เพราะมีการอ้างอิงถึงกัน):
    1) hr.department  — แผนก (ยังไม่ตั้ง parent_id / manager_id)
    2) hr.job         — ตำแหน่งงาน (อ้างแผนก)
    3) res.users      — ผู้ใช้ (*** ไม่ตั้งรหัสผ่าน *** ให้ผู้ใช้รีเซ็ตเอง)
    4) hr.employee    — พนักงาน (อ้างแผนก/ตำแหน่ง/ผู้ใช้)
    5) เชื่อมความสัมพันธ์ย้อนหลัง: แผนกแม่ / ผู้จัดการแผนก / ผู้จัดการพนักงาน

หมายเหตุ Odoo 19: ฟิลด์งานบุคคลจำนวนมาก (department_id / job_id / job_title /
identification_id / marital / sex / employee_type ฯลฯ) ย้ายไปเก็บบนโมเดล
`hr.version` แต่ `hr.employee` ใช้ `_inherits = {'hr.version': 'version_id'}`
จึงกำหนดค่าเหล่านี้ผ่าน ORM ได้โดยตรงเหมือนเดิม

ขอบเขตของ step นี้: นำเข้า "ตัวบุคคล/องค์กร" เท่านั้น
    * ไม่ผูกบทบาท/สิทธิ์ (res.users.role) — มอบหมายผ่าน UI หรือ step RBAC แยก
      เพื่อรักษาหลัก Segregation of Duties (ดู discovery doc section 3.6)
    * ไม่ตั้งรหัสผ่านคงที่ให้บัญชีใด ๆ
"""
import common

# บัญชีเทมเพลตมาตรฐานของ Odoo (base สร้างให้ทุกฐานข้อมูลอยู่แล้ว) — ไม่นำเข้าซ้ำ
_SKIP_LOGINS = {'__system__', 'public', 'portaltemplate', 'default'}

# ความยาวสูงสุดของชื่อ (กันข้อมูลเพี้ยนจากระบบเดิม)
_NAME_MAX = 250

# ค่าที่ยอมรับได้ของ sex / employee_type / marital (ตรงกับ Odoo 19)
_SEX_ALLOWED = {'male', 'female', 'other'}


# --------------------------------------------------------------------------
# ตัวช่วยอ่านข้อมูลจากระบบเดิม
# --------------------------------------------------------------------------
def _legacy_columns(table):
    """อ่านรายชื่อคอลัมน์จริงของตารางในระบบเดิม."""
    import legacy
    rows = legacy.fetch_all(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,))
    return {r['column_name'] for r in rows}


def _pick(cols, wanted):
    """กรองเหลือเฉพาะคอลัมน์ที่มีจริงในตารางเดิม (คงลำดับตาม wanted)."""
    return [c for c in wanted if c in cols]


def _text(raw):
    """แปลงค่าเป็นข้อความล้วน (คืนค่า False เมื่อว่าง)."""
    value = (raw or '').strip() if isinstance(raw, str) else raw
    return value or False


def _selection_values(model, field_name):
    """อ่านชุดค่าที่อนุญาตของฟิลด์ Selection ใน Odoo 19."""
    field = model._fields.get(field_name)
    if field is None or not field.selection:
        return set()
    selection = field.selection
    if callable(selection):
        selection = selection(model)
    return {key for key, _label in selection}


def _company_map():
    """สร้าง mapping รหัสบริษัทเดิม -> รหัสบริษัทใน Odoo 19 (fallback = บริษัทปัจจุบัน)."""
    import legacy
    env = common.odoo_env()
    rows = legacy.fetch_all("SELECT id FROM res_company ORDER BY id")
    existing = set(env['res.company'].search([]).ids)
    return {r['id']: (r['id'] if r['id'] in existing else None) for r in rows}


def _attach_xmlid(model, legacy_id, rec):
    """ผูก External ID ของการนำเข้ากับ record ที่มีอยู่แล้ว (กรณีพบข้อมูลซ้ำ)."""
    if common.DRY_RUN:
        return
    xmlid = common.get_xmlid(model, legacy_id)
    env = common.odoo_env()
    imd = env['ir.model.data']
    if imd._xmlid_to_res_id(xmlid, raise_if_not_found=False) == rec.id:
        return
    imd._update_xmlids(
        [{'xml_id': xmlid, 'record': rec, 'noupdate': True}], update=True)


def _upsert_employee(legacy_id, vals):
    """upsert พนักงาน โดยกันการชนข้อจำกัด unique(user_id, company_id)

    Odoo สร้างพนักงานตั้งต้นให้ผู้ดูแลระบบตอนติดตั้งโมดูล hr (เช่น 'Administrator')
    หากพนักงานจากระบบเดิมผูกกับผู้ใช้รายเดียวกัน จะ "รับช่วง" record เดิมแทนการสร้างซ้ำ
    """
    xmlid = common.get_xmlid('hr.employee', legacy_id)
    env = common.odoo_env()
    imd = env['ir.model.data']
    if imd._xmlid_to_res_id(xmlid, raise_if_not_found=False):
        return common.upsert('hr.employee', legacy_id, vals)

    user_id = vals.get('user_id')
    if user_id:
        Employee = env['hr.employee'].with_context(active_test=False)
        found = Employee.search(
            [('user_id', '=', user_id),
             ('company_id', '=', vals.get('company_id'))], limit=1)
        if found:
            common.log("พนักงาน '%s' (legacy id=%s) ผูกผู้ใช้ id=%s แล้ว — "
                       "รับช่วง record เดิม" % (found.name, legacy_id, user_id))
            if not common.DRY_RUN:
                changed = common._changed_values(env['hr.employee'], found, vals)
                if changed:
                    found.write(changed)
                _attach_xmlid('hr.employee', legacy_id, found)
            return found, 'updated'

    return common.upsert('hr.employee', legacy_id, vals)


# --------------------------------------------------------------------------
# 1) แผนก
# --------------------------------------------------------------------------
def _sync_departments(stats):
    """นำเข้า hr.department (ยังไม่ตั้ง parent_id / manager_id)."""
    import legacy
    cols = _legacy_columns('hr_department')
    wanted = _pick(cols, ['id', 'name', 'active', 'company_id', 'color', 'note'])
    short_col = 'dtr_department_short' if 'dtr_department_short' in cols else None
    if short_col:
        wanted.append(short_col)
    rows = legacy.fetch_all(
        "SELECT %s FROM hr_department ORDER BY id" % ', '.join(wanted))

    env = common.odoo_env()
    has_code = 'code' in env['hr.department']._fields
    if short_col and not has_code:
        common.log("คำเตือน: Odoo 19 ไม่มีฟิลด์ hr.department.code — "
                   "จะไม่นำเข้ารหัสย่อแผนก (ตรวจว่าติดตั้ง od19_security_roles)")
    companies = _company_map()

    result = {}
    for row in rows:
        name = _text(row.get('name'))
        if not name:
            common.log("ข้ามแผนก legacy id=%s เพราะไม่มีชื่อ" % row.get('id'))
            stats.skipped += 1
            continue
        vals = {
            'name': name[:_NAME_MAX],
            'active': bool(row.get('active')),
        }
        company_id = companies.get(row.get('company_id')) or env.company.id
        vals['company_id'] = company_id
        if row.get('color'):
            vals['color'] = row['color']
        note = _text(row.get('note'))
        if note:
            vals['note'] = note
        if short_col and has_code:
            code = _text(row.get(short_col))
            if code:
                vals['code'] = code[:_NAME_MAX]

        rec, action = common.upsert('hr.department', row['id'], vals)
        stats.bump(action)
        result[row['id']] = rec.id if rec else None

    common.log("แผนก: พบ %d แผนก นำเข้าสำเร็จ %d"
               % (len(rows), len([v for v in result.values() if v])))
    return result


# --------------------------------------------------------------------------
# 2) ตำแหน่งงาน
# --------------------------------------------------------------------------
def _sync_jobs(stats, dept_ids):
    """นำเข้า hr.job (อ้างแผนก); unique(name, company) → กันชื่อซ้ำก่อน upsert."""
    import legacy
    cols = _legacy_columns('hr_job')
    wanted = _pick(cols, ['id', 'name', 'department_id', 'sequence', 'description',
                          'requirements', 'active', 'company_id'])
    rows = legacy.fetch_all(
        "SELECT %s FROM hr_job ORDER BY id" % ', '.join(wanted))

    env = common.odoo_env()
    companies = _company_map()

    result = {}          # legacy_id -> od19 id
    first_key = {}       # (ชื่อ, บริษัท) -> od19 id (แถวแรกที่นำเข้าสำเร็จ)
    for row in rows:
        name = _text(row.get('name'))
        if not name:
            common.log("ข้ามตำแหน่งงาน legacy id=%s เพราะไม่มีชื่อ" % row.get('id'))
            stats.skipped += 1
            continue
        name = name[:_NAME_MAX]
        company_id = companies.get(row.get('company_id')) or env.company.id
        key = (name.casefold(), company_id)
        if key in first_key:
            # ชื่อซ้ำ (unique(name, company)) — ชี้ legacy id ไปที่ record แรกแทน
            common.log("ตำแหน่งงาน '%s' ซ้ำ (legacy id=%s) — ใช้ record เดิม"
                       % (name, row['id']))
            stats.skipped += 1
            result[row['id']] = first_key[key]
            continue

        vals = {
            'name': name,
            'company_id': company_id,
            'active': bool(row.get('active')),
        }
        dept = dept_ids.get(row.get('department_id'))
        if dept:
            vals['department_id'] = dept
        if row.get('sequence'):
            vals['sequence'] = row['sequence']
        description = _text(row.get('description'))
        if description:
            vals['description'] = description
        requirements = _text(row.get('requirements'))
        if requirements:
            vals['requirements'] = requirements

        rec, action = common.upsert('hr.job', row['id'], vals)
        stats.bump(action)
        if rec:
            result[row['id']] = rec.id
            first_key[key] = rec.id
        else:
            result[row['id']] = None

    common.log("ตำแหน่งงาน: พบ %d ตำแหน่ง นำเข้าสำเร็จ %d"
               % (len(rows), len(first_key)))
    return result


# --------------------------------------------------------------------------
# 3) ผู้ใช้
# --------------------------------------------------------------------------
def _sync_users(stats):
    """นำเข้าผู้ใช้ (login/ชื่อ/บริษัท/สถานะ) — ไม่ตั้งรหัสผ่าน และไม่ผูกบทบาท."""
    import legacy
    rows = legacy.fetch_all(
        "SELECT u.id, u.login, u.active, u.company_id, u.share, p.name AS partner_name "
        "FROM res_users u LEFT JOIN res_partner p ON p.id = u.partner_id "
        "ORDER BY u.id")

    env = common.odoo_env()
    Users = env['res.users']
    portal_group = env.ref('base.group_portal', raise_if_not_found=False)
    companies = _company_map()

    result = {}
    for row in rows:
        login = _text(row.get('login'))
        if not login:
            common.log("ข้ามผู้ใช้ legacy id=%s เพราะไม่มี login" % row.get('id'))
            stats.skipped += 1
            continue
        if login in _SKIP_LOGINS:
            common.log("ข้ามบัญชีเทมเพลต '%s' (Odoo สร้างไว้แล้ว)" % login)
            stats.skipped += 1
            continue

        existing = Users.with_context(active_test=False).search(
            [('login', '=', login)], limit=1)
        if existing:
            _attach_xmlid('res.users', row['id'], existing)
            common.log("พบบัญชี '%s' ใน Odoo 19 แล้ว — ผูก External ID "
                       "โดยไม่แก้ข้อมูลเดิม" % login)
            stats.bump('updated')
            result[row['id']] = existing.id
            continue

        name = _text(row.get('partner_name')) or login
        vals = {
            'login': login,
            'name': name[:_NAME_MAX],
            'active': bool(row.get('active')),
        }
        vals['company_id'] = companies.get(row.get('company_id')) or env.company.id
        # ผู้ใช้ภายนอก (share) ต้องอยู่กลุ่มพอร์ทัล ส่วนผู้ใช้ภายในใช้ค่าเริ่มต้น
        # ของระบบ (base_user_role จะกำหนดบทบาทเริ่มต้นให้เอง)
        if row.get('share') and portal_group:
            from odoo import Command
            vals['group_ids'] = [Command.set([portal_group.id])]

        rec, action = common.upsert('res.users', row['id'], vals)
        stats.bump(action)
        result[row['id']] = rec.id if rec else None

    common.log("ผู้ใช้: พบ %d บัญชี นำเข้าใหม่/ผูกแล้ว %d"
               % (len(rows), len([v for v in result.values() if v])))
    return result


# --------------------------------------------------------------------------
# 4) พนักงาน
# --------------------------------------------------------------------------
def _sync_employees(stats, dept_ids, job_ids, user_ids):
    """นำเข้า hr.employee (อ้างแผนก/ตำแหน่ง/ผู้ใช้)."""
    import legacy
    cols = _legacy_columns('hr_employee')
    wanted = _pick(cols, [
        'id', 'name', 'active', 'company_id', 'department_id', 'job_id',
        'job_title', 'work_email', 'work_phone', 'mobile_phone', 'barcode', 'pin',
        'identification_id', 'ssnid', 'passport_id', 'birthday', 'gender', 'marital',
        'place_of_birth', 'employee_type', 'user_id', 'parent_id',
        'spouse_complete_name', 'spouse_birthdate', 'children', 'additional_note',
        'emp_code', 'name_en', 'x_name_th',
    ])
    rows = legacy.fetch_all(
        "SELECT %s FROM hr_employee ORDER BY id" % ', '.join(wanted))

    env = common.odoo_env()
    emp_fields = env['hr.employee']._fields
    marital_allowed = _selection_values(env['hr.employee'], 'marital')
    type_allowed = _selection_values(env['hr.employee'], 'employee_type')
    companies = _company_map()

    result = {}
    for row in rows:
        name = _text(row.get('name'))
        if not name:
            common.log("ข้ามพนักงาน legacy id=%s เพราะไม่มีชื่อ" % row.get('id'))
            stats.skipped += 1
            continue

        vals = {
            'name': name[:_NAME_MAX],
            'active': bool(row.get('active')),
            'company_id': companies.get(row.get('company_id')) or env.company.id,
        }

        dept = dept_ids.get(row.get('department_id'))
        if dept:
            vals['department_id'] = dept
        job = job_ids.get(row.get('job_id'))
        if job:
            vals['job_id'] = job

        for src, dst in (('work_email', 'work_email'),
                         ('work_phone', 'work_phone'),
                         ('mobile_phone', 'mobile_phone'),
                         ('barcode', 'barcode'),
                         ('pin', 'pin'),
                         ('identification_id', 'identification_id'),
                         ('ssnid', 'ssnid'),
                         ('passport_id', 'passport_id'),
                         ('birthday', 'birthday'),
                         ('place_of_birth', 'place_of_birth'),
                         ('spouse_complete_name', 'spouse_complete_name'),
                         ('spouse_birthdate', 'spouse_birthdate'),
                         ('additional_note', 'additional_note'),
                         ('emp_code', 'emp_code'),
                         ('name_en', 'name_en'),
                         ('x_name_th', 'x_name_th')):
            if dst not in emp_fields:
                continue
            value = _text(row.get(src))
            if value:
                vals[dst] = value[:_NAME_MAX] if isinstance(value, str) else value

        if row.get('children'):
            vals['children'] = row['children']

        gender = _text(row.get('gender'))
        if gender in _SEX_ALLOWED and 'sex' in emp_fields:
            vals['sex'] = gender

        marital = _text(row.get('marital'))
        if marital and (not marital_allowed or marital in marital_allowed):
            vals['marital'] = marital

        employee_type = _text(row.get('employee_type'))
        if employee_type and (not type_allowed or employee_type in type_allowed):
            vals['employee_type'] = employee_type

        user = user_ids.get(row.get('user_id'))
        if user:
            vals['user_id'] = user

        rec, action = _upsert_employee(row['id'], vals)
        stats.bump(action)
        result[row['id']] = rec.id if rec else None

    # ค่า job_title ที่ไม่ตรงกับชื่อตำแหน่งงาน — เขียนแยกหลังสร้าง employee
    _apply_custom_job_titles(rows, job_ids, result, stats)

    common.log("พนักงาน: พบ %d คน นำเข้า/ผูกแล้ว %d"
               % (len(rows), len([v for v in result.values() if v])))
    return result


def _apply_custom_job_titles(rows, job_ids, emp_ids, stats):
    """ตั้ง job_title ให้ตรงกับระบบเดิม (เมื่อไม่ตรงกับชื่อตำแหน่งงานมาตรฐาน)."""
    env = common.odoo_env()
    Job = env['hr.job']
    Employee = env['hr.employee']
    for row in rows:
        title = _text(row.get('job_title'))
        if not title:
            continue
        emp_id = emp_ids.get(row.get('id'))
        if not emp_id:
            continue
        job_id = job_ids.get(row.get('job_id'))
        job_name = Job.browse(job_id).name if job_id else False
        if job_name and title.casefold() == job_name.casefold():
            continue
        emp = Employee.browse(emp_id)
        if emp.job_title != title:
            if common.DRY_RUN:
                continue
            emp.write({'job_title': title[:_NAME_MAX]})


# --------------------------------------------------------------------------
# 5) เชื่อมความสัมพันธ์ย้อนหลัง
# --------------------------------------------------------------------------
def _link_relations(stats, dept_ids, emp_ids):
    """ตั้งค่า parent_id ของแผนก, manager_id ของแผนก และผู้จัดการของพนักงาน."""
    import legacy
    env = common.odoo_env()

    # 5.1 แผนกแม่ (parent_id)
    if 'parent_id' in _legacy_columns('hr_department'):
        rows = legacy.fetch_all(
            "SELECT id, parent_id FROM hr_department WHERE parent_id IS NOT NULL "
            "ORDER BY id")
        Dept = env['hr.department']
        for row in rows:
            child = dept_ids.get(row['id'])
            parent = dept_ids.get(row['parent_id'])
            if not child or not parent or child == parent:
                continue
            rec = Dept.browse(child)
            if rec.parent_id.id != parent:
                if common.DRY_RUN:
                    continue
                rec.write({'parent_id': parent})
            stats.bump('updated')

    # 5.2 ผู้จัดการแผนก (manager_id) — อ้างพนักงาน
    if 'manager_id' in _legacy_columns('hr_department'):
        rows = legacy.fetch_all(
            "SELECT id, manager_id FROM hr_department WHERE manager_id IS NOT NULL "
            "ORDER BY id")
        Dept = env['hr.department']
        for row in rows:
            dept = dept_ids.get(row['id'])
            manager = emp_ids.get(row['manager_id'])
            if not dept or not manager:
                continue
            rec = Dept.browse(dept)
            if rec.manager_id.id != manager:
                if common.DRY_RUN:
                    continue
                rec.write({'manager_id': manager})

    # 5.3 ผู้จัดการ/หัวหน้าของพนักงาน (parent_id) — อ้างพนักงาน
    rows = legacy.fetch_all(
        "SELECT id, parent_id FROM hr_employee WHERE parent_id IS NOT NULL ORDER BY id")
    Employee = env['hr.employee']
    for row in rows:
        emp = emp_ids.get(row['id'])
        manager = emp_ids.get(row['parent_id'])
        if not emp or not manager or emp == manager:
            continue
        rec = Employee.browse(emp)
        if rec.parent_id.id != manager:
            if common.DRY_RUN:
                continue
            rec.write({'parent_id': manager})

    common.log("เชื่อมความสัมพันธ์ (แผนกแม่/ผู้จัดการ) เรียบร้อย")


# --------------------------------------------------------------------------
# จุดเริ่มต้นของ step
# --------------------------------------------------------------------------
def run(stats):
    common.log("s06_people: เริ่มนำเข้าบุคลากร (แผนก/ตำแหน่ง/ผู้ใช้/พนักงาน)")
    dept_ids = _sync_departments(stats)
    job_ids = _sync_jobs(stats, dept_ids)
    user_ids = _sync_users(stats)
    emp_ids = _sync_employees(stats, dept_ids, job_ids, user_ids)
    _link_relations(stats, dept_ids, emp_ids)
    common.log("s06_people: เสร็จสิ้น")

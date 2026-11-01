# -*- coding: utf-8 -*-
"""s60_hr — แผนก พนักงาน การลงเวลา ลา ค่าใช้จ่าย และการรับสมัคร"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def _dt(offset=0, hour=8):
    return (datetime.datetime.now() + datetime.timedelta(days=offset)).replace(
        hour=hour, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')


def _dt_val(offset=0, hour=8):
    """คืนค่าเป็น datetime object (hr.leave ต้องใช้ datetime ไม่ใช่ string)."""
    return (datetime.datetime.now() + datetime.timedelta(days=offset)).replace(
        hour=hour, minute=0, second=0, microsecond=0)


_DEPTS = [
    ('dept_01', 'ฝ่ายบริหาร'), ('dept_02', 'ฝ่ายบัญชีและการเงิน'),
    ('dept_03', 'ฝ่ายขาย'), ('dept_04', 'ฝ่ายจัดซื้อ'),
    ('dept_05', 'ฝ่ายผลิต'), ('dept_06', 'ฝ่ายคลังสินค้า'),
    ('dept_07', 'ฝ่ายซ่อมบำรุง'), ('dept_08', 'ฝ่ายบุคคล'),
    ('dept_09', 'ฝ่ายคุณภาพ (QA/QC)'), ('dept_10', 'ฝ่ายไอที'),
]

_EMPS = [
    ('emp_01', 'นายสมชาย ใจดี', 'dept_01', 'ผู้จัดการทั่วไป'),
    ('emp_02', 'นางสาววิภา รักไทย', 'dept_02', 'หัวหน้าฝ่ายบัญชี'),
    ('emp_03', 'นายประเสริฐ มั่งมี', 'dept_03', 'ผู้จัดการฝ่ายขาย'),
    ('emp_04', 'นางสาวอรทัย ดีเลิศ', 'dept_04', 'เจ้าหน้าที่จัดซื้อ'),
    ('emp_05', 'นายวีระ ชัยชนะ', 'dept_05', 'หัวหน้าโรงงาน'),
    ('emp_06', 'นางสาวกนกวรรณ สุขใจ', 'dept_06', 'หัวหน้าคลังสินค้า'),
    ('emp_07', 'นายธนากร พูลทรัพย์', 'dept_07', 'ช่างซ่อมบำรุง'),
    ('emp_08', 'นางสาวปิยะดา แสงทอง', 'dept_08', 'เจ้าหน้าที่บุคคล'),
    ('emp_09', 'นายอนุชา เก่งกาจ', 'dept_09', 'วิศวกรคุณภาพ'),
    ('emp_10', 'นายภาคิน วงศ์ไพศาล', 'dept_10', 'ผู้ดูแลระบบไอที'),
]


def run(ctx):
    ctx.step('s60_hr', 'แผนก พนักงาน การลงเวลา ลา ค่าใช้จ่าย')
    depts = {}
    if ctx.has('hr.department'):
        for key, name in _DEPTS:
            rec = ctx.upsert('hr.department', key, {'name': name})
            if rec:
                depts[key] = rec
        ctx.log("แผนก: %d" % len(depts))

    # ประเภทการลา (ต้องมีก่อนสร้างใบลา)
    # ตั้ง requires_allocation=False เพื่อให้สร้างใบลาตัวอย่างได้โดยไม่ต้องมี allocation
    leave_types = []
    if ctx.has('hr.leave.type'):
        for key, name, unit, alloc in [('lt_annual', 'ลาพักร้อนประจำปี', 'day', False),
                                       ('lt_sick', 'ลาป่วย', 'day', False),
                                       ('lt_personal', 'ลากิจ', 'day', False)]:
            rec = ctx.upsert('hr.leave.type', key, {
                'name': name, 'request_unit': unit,
                'employee_requests': True, 'requires_allocation': alloc})
            if rec:
                leave_types.append(rec)

    employees = []
    if ctx.has('hr.employee'):
        for key, name, dkey, job in _EMPS:
            dept = depts.get(dkey)
            vals = {'name': name, 'job_title': job,
                    'work_email': '%s@example.co.th' % key,
                    'department_id': dept.id if dept else False}
            rec = ctx.upsert('hr.employee', key, vals)
            if rec:
                employees.append(rec)
        ctx.log("พนักงาน: %d" % len(employees))

    # ---------------- การลงเวลา (ZKTeco-style) ----------------
    if ctx.has('hr.attendance') and employees:
        made = 0
        for i in range(10):
            emp = employees[i % len(employees)]
            vals = {'employee_id': emp.id, 'check_in': _dt(-i, 8), 'check_out': _dt(-i, 17)}
            if ctx.upsert('hr.attendance', 'att_%02d' % (i + 1), vals):
                made += 1
        ctx.log("การลงเวลา: %d" % made)

    # ---------------- ใบลา ----------------
    if ctx.has('hr.leave') and employees and leave_types:
        made = 0
        for i in range(10):
            emp = employees[i % len(employees)]
            lt = leave_types[i % len(leave_types)]
            vals = {
                'employee_id': emp.id, 'holiday_status_id': lt.id,
                'date_from': _dt_val(5 + i, 8), 'date_to': _dt_val(6 + i, 17),
                'name': 'คำขอลาทดสอบ %02d' % (i + 1),
            }
            if ctx.upsert('hr.leave', 'leave_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบลา: %d" % made)

    # ---------------- ค่าใช้จ่าย ----------------
    if ctx.has('hr.expense') and employees:
        prod = ctx.find('product.product', [('type', '=', 'service')], limit=1) or ctx.find('product.product', [], limit=1)
        made = 0
        for i in range(10):
            emp = employees[i % len(employees)]
            vals = {
                'name': 'ค่าใช้จ่ายทดสอบ %02d (ค่าเดินทาง)' % (i + 1),
                'employee_id': emp.id,
                'company_id': ctx.company.id,
                'payment_mode': 'own_account',
                'quantity': 1.0,
                'unit_amount': 500.0 + i * 150,
                'date': _d(-20 + i),
                'product_id': prod.id if prod else False,
            }
            if ctx.upsert('hr.expense', 'exp_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ค่าใช้จ่ายพนักงาน: %d" % made)

    # ---------------- ตำแหน่งงาน + ใบสมัคร ----------------
    jobs = []
    if ctx.has('hr.job'):
        for key, name in [('job_01', 'วิศวกรซ่อมบำรุง'), ('job_02', 'เจ้าหน้าที่ขาย'),
                          ('job_03', 'เจ้าหน้าที่บัญชี')]:
            rec = ctx.upsert('hr.job', key, {'name': name})
            if rec:
                jobs.append(rec)
        ctx.log("ตำแหน่งงาน: %d" % len(jobs))

    if ctx.has('hr.applicant'):
        made = 0
        names = ['นายกิตติศักดิ์ รุ่งเรือง', 'นางสาวมณีรัตน์ สว่างใจ', 'นายชัยวัฒน์ เพียรดี',
                 'นางสาวศิริพร นาคทอง', 'นายปกรณ์ ตั้งใจ', 'นางสาวเจนจิรา สุขสันต์',
                 'นายสมปอง ทองดี', 'นางสาวรัตนา ใจงาม', 'นายเทพชัย กล้าหาญ', 'นางสาวกมลชนก พรหมมา']
        for i in range(10):
            vals = {
                'partner_name': names[i],
                'email_from': 'applicant%02d@example.com' % (i + 1),
                'job_id': jobs[i % len(jobs)].id if jobs else False,
                'kanban_state': 'normal',
            }
            if ctx.upsert('hr.applicant', 'appl_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบสมัครงาน: %d" % made)

    ctx.state['employees'] = employees
    ctx.state['departments'] = depts

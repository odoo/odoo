# -*- coding: utf-8 -*-
"""s70_project_helpdesk — โครงการ งานย่อย บัญชีวิเคราะห์ และ Helpdesk"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


_PROJECTS = [
    ('proj_01', 'โครงการติดตั้งแอร์ อาคาร A', 'job'),
    ('proj_02', 'โครงการบำรุงรักษาประจำปี ลูกค้า X', 'pm'),
    ('proj_03', 'โครงการระบบทำความเย็น โรงงาน Y', 'sale'),
    ('proj_04', 'งานบริการซ่อม (Ad-hoc)', 'service'),
    ('proj_05', 'โครงการก่อสร้างอาคารสำนักงาน Z', 'job'),
    ('proj_06', 'โครงการวางระบบแอร์ โรงพยาบาล', 'sale'),
    ('proj_07', 'โครงการบำรุงรักษาแอร์ อาคาร B', 'pm'),
    ('proj_08', 'งานบริการล้างแอร์ (รายครั้ง)', 'service'),
    ('proj_09', 'โครงการติดตั้งระบบปรับอากาศ โรงแรม W', 'job'),
    ('proj_10', 'โครงการขายและติดตั้ง อาคารพาณิชย์ V', 'sale'),
]


def run(ctx):
    ctx.step('s70_project_helpdesk', 'โครงการ งานย่อย และ Helpdesk')
    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    employees = ctx.state.get('employees') or list(ctx.find('hr.employee', [], limit=10))

    # ---------------- บัญชีวิเคราะห์ ----------------
    if ctx.has('account.analytic.account'):
        plan = ctx.find('account.analytic.plan', [], limit=1)
        made = 0
        for i in range(10):
            vals = {'name': 'AA-%03d บัญชีวิเคราะห์ตัวอย่าง' % (i + 1),
                    'plan_id': plan.id if plan else False}
            if ctx.upsert('account.analytic.account', 'aa_%02d' % (i + 1), vals):
                made += 1
        ctx.log("บัญชีวิเคราะห์: %d" % made)

    # ---------------- โครงการ ----------------
    projects = []
    if ctx.has('project.project'):
        for i, (key, name, ptype) in enumerate(_PROJECTS):
            partner = customers[i % len(customers)] if customers else None
            vals = {'name': name, 'od19_project_type': ptype,
                    'privacy_visibility': 'employees',
                    'partner_id': partner.id if partner else False}
            # โครงการประเภท 'sale' ต้องมีเลขงาน (job_no) — กำหนดตรงเพื่อไม่ต้องตั้ง sequence ผู้ขาย
            if ptype == 'sale':
                vals['job_no'] = 'S%02d-%04d' % (i + 1, 1001 + i)
            rec = ctx.upsert('project.project', key, vals)
            if rec:
                projects.append(rec)
        ctx.log("โครงการ: %d" % len(projects))

    # ---------------- งานย่อย ----------------
    if ctx.has('project.task') and projects:
        made = 0
        for i in range(10):
            proj = projects[i % len(projects)]
            vals = {'name': 'งานย่อยที่ %02d — ตรวจสอบหน้างาน' % (i + 1),
                    'project_id': proj.id,
                    'date_deadline': _d(7 + i)}
            if ctx.upsert('project.task', 'task_%02d' % (i + 1), vals):
                made += 1
        ctx.log("งานย่อย: %d" % made)

    # ---------------- Helpdesk ----------------
    if ctx.has('helpdesk.ticket'):
        made = 0
        subjects = ['แอร์ไม่เย็น', 'มีเสียงดังผิดปกติ', 'น้ำยาแอร์รั่ว', 'รีโมทใช้งานไม่ได้',
                    'แอร์มีน้ำหยด', 'คอมเพรสเซอร์ไม่ทำงาน', 'ต้องการล้างแอร์', 'ไฟเลี้ยงไม่ติด',
                    'แจ้งซ่อมด่วน', 'ขอตรวจเช็คประจำปี']
        for i in range(10):
            partner = customers[i % len(customers)] if customers else None
            emp = employees[i % len(employees)] if employees else None
            vals = {
                'name': '%s — %s' % (subjects[i], (partner.name if partner else 'ลูกค้าทั่วไป')),
                'visibility': 'public',
                'description': '<p>รายละเอียดปัญหา (ข้อมูลทดสอบ seed)</p>',
                'partner_id': partner.id if partner else False,
                'service_type': 'repair',
            }
            if ctx.upsert('helpdesk.ticket', 'ticket_%02d' % (i + 1), vals):
                made += 1
        ctx.log("Helpdesk ticket: %d" % made)

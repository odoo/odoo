# -*- coding: utf-8 -*-
"""s80_iso — ระบบ ISO 9001/14001: ความเสี่ยง เอกสาร การฝึกอบรม เครื่องมือวัด
ข้อบกพร่อง (NCR) การตรวจประเมินภายใน ซัพพลายเออร์ และความพึงพอใจลูกค้า
"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def run(ctx):
    ctx.step('s80_iso', 'ระบบ ISO (ความเสี่ยง/เอกสาร/ฝึกอบรม/เครื่องมือวัด/NCR/ตรวจประเมิน)')
    employees = ctx.state.get('employees') or list(ctx.find('hr.employee', [], limit=10))
    vendors = ctx.state.get('vendors') or list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))
    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    depts_map = ctx.state.get('departments') or {}
    depts = [d for d in depts_map.values()] or list(ctx.find('hr.department', [], limit=10))

    def emp(i):
        return employees[i % len(employees)] if employees else None

    def dep(i):
        return depts[i % len(depts)] if depts else None

    # ---------------- มาตรฐาน + หมวดเอกสาร + เอกสาร ----------------
    if ctx.has('od19.iso.standard'):
        for key, code, name in [('std_01', 'ISO9001:2015', 'ระบบบริหารคุณภาพ'),
                                ('std_02', 'ISO14001:2015', 'ระบบบริหารสิ่งแวดล้อม')]:
            ctx.upsert('od19.iso.standard', key, {'name': name, 'code': code})

    cats = []
    if ctx.has('od19.iso.document.category'):
        for i, (key, name, prefix) in enumerate([
                ('dcat_01', 'เอกสารคุณภาพ', 'QM'), ('dcat_02', 'คู่มือการปฏิบัติงาน', 'WI'),
                ('dcat_03', 'แบบฟอร์ม', 'FM'), ('dcat_04', 'ระเบียบปฏิบัติ', 'PR'),
                ('dcat_05', 'เอกสารสิ่งแวดล้อม', 'EM')]):
            rec = ctx.upsert('od19.iso.document.category', key, {'name': name, 'prefix': prefix})
            if rec:
                cats.append(rec)

    if ctx.has('od19.iso.document') and cats:
        statuses = ['draft', 'review', 'approval', 'approved', 'approved',
                    'approved', 'final_approval', 'approved', 'obsolete', 'draft']
        made = 0
        for i in range(10):
            cat = cats[i % len(cats)]
            # กำหนดรหัสเองไม่ให้ซ้ำ (ระบบจะสร้างรหัสจาก sequence ถ้าไม่ส่งมา
            # แต่ sequence ของแต่ละ prefix อาจไม่มี ทำให้ได้รหัสซ้ำกัน)
            vals = {
                'document_title': 'เอกสาร ISO ลำดับที่ %02d' % (i + 1),
                'category_id': cat.id,
                'code': '%s-XX-%03d' % ((cat.prefix or 'DOC'), i + 1),
                'revision': '%02d' % (i % 3),
                'status': statuses[i],
            }
            if ctx.upsert('od19.iso.document', 'doc_%02d' % (i + 1), vals):
                made += 1
        ctx.log("เอกสาร ISO: %d" % made)

    # ---------------- ความเสี่ยง ----------------
    risks = []
    if ctx.has('od19.iso.risk'):
        cats_r = ['operational', 'quality', 'environment', 'safety', 'compliance',
                  'financial', 'supply_chain', 'technology', 'strategic', 'reputational']
        states = ['draft', 'identified', 'analyzed', 'evaluated', 'treated',
                  'monitored', 'closed', 'identified', 'analyzed', 'treated']
        for i in range(10):
            vals = {
                'name': 'RSK-%03d' % (i + 1),
                'title': 'ความเสี่ยงด้าน%s ลำดับ %02d' % (cats_r[i], i + 1),
                'risk_type': 'risk' if i < 8 else 'opportunity',
                'category': cats_r[i],
                'description': 'รายละเอียดความเสี่ยง (ข้อมูลทดสอบ seed)',
                'state': states[i],
                'severity': str((i % 5) + 1),
                'probability': str((i % 5) + 1),
            }
            rec = ctx.upsert('od19.iso.risk', 'risk_%02d' % (i + 1), vals)
            if rec:
                risks.append(rec)
        ctx.log("ความเสี่ยง: %d" % len(risks))

        if ctx.has('od19.iso.risk.action') and risks:
            for i, r in enumerate(risks):
                ctx.upsert('od19.iso.risk.action', 'risk_act_%02d' % (i + 1), {
                    'risk_id': r.id,
                    'action': 'มาตรการจัดการความเสี่ยงลำดับ %02d' % (i + 1),
                    'status': ['pending', 'in_progress', 'done'][i % 3],
                })

    # ---------------- การฝึกอบรม ----------------
    courses = []
    if ctx.has('od19.iso.training.course'):
        ctypes = ['internal', 'external', 'online', 'on_job']
        cstates = ['draft', 'planned', 'in_progress', 'completed', 'completed']
        for i in range(10):
            vals = {
                'name': 'หลักสูตรฝึกอบรม ลำดับ %02d' % (i + 1),
                'course_type': ctypes[i % len(ctypes)],
                'date': _d(-60 + i * 5),
                'state': cstates[i % len(cstates)],
            }
            rec = ctx.upsert('od19.iso.training.course', 'course_%02d' % (i + 1), vals)
            if rec:
                courses.append(rec)
        ctx.log("หลักสูตรฝึกอบรม: %d" % len(courses))

        if ctx.has('od19.iso.training.participant') and courses and employees:
            made = 0
            for i in range(10):
                c = courses[i % len(courses)]
                e = emp(i)
                if not e:
                    continue
                if ctx.upsert('od19.iso.training.participant', 'tpart_%02d' % (i + 1), {
                        'course_id': c.id, 'employee_id': e.id}):
                    made += 1
            ctx.log("ผู้เข้าอบรม: %d" % made)

    # ---------------- เครื่องมือวัด (Calibration) ----------------
    equip = []
    if ctx.has('od19.iso.calibration.equipment'):
        ecats = ['dimensional', 'temperature', 'pressure', 'electrical', 'weight', 'flow']
        for i in range(10):
            vals = {
                'name': 'เครื่องมือวัด ลำดับ %02d' % (i + 1),
                'code': 'EQ-%04d' % (i + 1),
                'category': ecats[i % len(ecats)],
                'state': 'active' if i < 9 else 'out_of_service',
            }
            rec = ctx.upsert('od19.iso.calibration.equipment', 'equip_%02d' % (i + 1), vals)
            if rec:
                equip.append(rec)
        ctx.log("เครื่องมือวัด: %d" % len(equip))

        if ctx.has('od19.iso.calibration.record') and equip:
            made = 0
            for i in range(10):
                if ctx.upsert('od19.iso.calibration.record', 'cal_%02d' % (i + 1), {
                        'name': 'CAL-%04d' % (i + 1),
                        'equipment_id': equip[i % len(equip)].id,
                        'date': _d(-90 + i * 9),
                        'calibration_type': ['internal', 'external', 'self'][i % 3],
                        'status': ['draft', 'scheduled', 'in_progress', 'passed', 'failed'][i % 5]}):
                    made += 1
            ctx.log("บันทึกสอบเทียบ: %d" % made)

    # ---------------- ข้อบกพร่อง (NCR) ----------------
    ncs = []
    if ctx.has('od19.iso.nonconformity'):
        ncats = ['quality', 'environment', 'safety', 'document', 'process', 'equipment', 'personnel', 'supplier']
        nsrc = ['internal_audit', 'external_audit', 'customer_complaint', 'process', 'incoming', 'final']
        nstates = ['draft', 'open', 'analysis', 'action', 'verification', 'closed']
        user = ctx.user_admin()
        for i in range(10):
            state = nstates[i % len(nstates)]
            vals = {
                'name': 'NCR-%03d' % (i + 1),
                'title': 'ข้อบกพร่องด้าน%s ลำดับ %02d' % (ncats[i % len(ncats)], i + 1),
                'category': ncats[i % len(ncats)],
                'severity': ['minor', 'major', 'critical'][i % 3],
                'source': nsrc[i % len(nsrc)],
                'state': state,
                'description': 'รายละเอียดข้อบกพร่อง (ข้อมูลทดสอบ seed)',
                'due_date': _d(-5 + i),
                'action_date': _d(-8 + i),
                'verified_by_id': user.id,
            }
            # ปิดข้อบกพร่องได้ต้องมีวันที่ตรวจสอบ (ตาม constraint)
            if state == 'closed':
                vals['verification_date'] = _d(-3 + i)
                vals['close_date'] = _d(-1 + i)
                vals['effective'] = True
            rec = ctx.upsert('od19.iso.nonconformity', 'nc_%02d' % (i + 1), vals)
            if rec:
                ncs.append(rec)
        ctx.log("ข้อบกพร่อง (NCR): %d" % len(ncs))

        if ctx.has('od19.iso.nc.action') and ncs:
            for i, n in enumerate(ncs):
                ctx.upsert('od19.iso.nc.action', 'nc_act_%02d' % (i + 1), {
                    'nc_id': n.id,
                    'action': 'การแก้ไขข้อบกพร่องลำดับ %02d' % (i + 1),
                    'action_type': ['corrective', 'preventive', 'improvement'][i % 3],
                    'status': ['pending', 'in_progress', 'done'][i % 3],
                })

    # ---------------- โปรแกรม + การตรวจประเมินภายใน ----------------
    if ctx.has('od19.iso.audit.program'):
        ctx.upsert('od19.iso.audit.program', 'audit_prog_01', {
            'name': 'โปรแกรมการตรวจประเมินภายใน ปี %d' % datetime.date.today().year,
            'year': datetime.date.today().year, 'state': 'approved'})

    audits = []
    if ctx.has('od19.iso.audit') and depts:
        atypes = ['system', 'process', 'product', 'compliance']
        astates = ['draft', 'planned', 'in_progress', 'report', 'follow_up', 'closed']
        auditor = ctx.user_admin()  # lead_auditor_id เป็น res.users (ไม่ใช่ hr.employee)
        for i in range(10):
            d = dep(i)
            vals = {
                'name': 'AUD-%03d' % (i + 1),
                'title': 'การตรวจประเมินภายใน ลำดับ %02d' % (i + 1),
                'audit_type': atypes[i % len(atypes)],
                'state': astates[i % len(astates)],
                'date_planned': _d(10 + i * 3),
                'lead_auditor_id': auditor.id,
                'auditee_department_id': d.id if d else False,
            }
            rec = ctx.upsert('od19.iso.audit', 'audit_%02d' % (i + 1), vals)
            if rec:
                audits.append(rec)
        ctx.log("การตรวจประเมิน: %d" % len(audits))

        if ctx.has('od19.iso.audit.finding') and audits:
            for i, a in enumerate(audits):
                ctx.upsert('od19.iso.audit.finding', 'find_%02d' % (i + 1), {
                    'audit_id': a.id,
                    'name': 'สิ่งที่พบจากการตรวจ ลำดับ %02d' % (i + 1),
                    'severity': ['minor', 'major', 'observation'][i % 3] if False else 'minor',
                    'status': ['open', 'in_progress', 'verified', 'closed'][i % 4],
                })

    # ---------------- ประเมินซัพพลายเออร์ ----------------
    evals = []
    if ctx.has('od19.iso.supplier.evaluation') and vendors:
        etypes = ['initial', 'periodic', 're-evaluation', 'special']
        estatus = ['draft', 'in_progress', 'done', 'done']
        for i in range(10):
            vals = {
                'name': 'SEV-%03d' % (i + 1),
                'partner_id': vendors[i % len(vendors)].id,
                'eval_type': etypes[i % len(etypes)],
                'date': _d(-120 + i * 10),
                'status': estatus[i % len(estatus)],
            }
            rec = ctx.upsert('od19.iso.supplier.evaluation', 'eval_%02d' % (i + 1), vals)
            if rec:
                evals.append(rec)
        ctx.log("ประเมินซัพพลายเออร์: %d" % len(evals))

        if ctx.has('od19.iso.supplier.eval.criteria') and evals:
            crit_cats = ['quality', 'delivery', 'price', 'service', 'environment']
            for i, e in enumerate(evals):
                for j in range(2):
                    ctx.upsert('od19.iso.supplier.eval.criteria', 'scrit_%02d_%d' % (i + 1, j + 1), {
                        'evaluation_id': e.id,
                        'name': 'เกณฑ์ %s' % crit_cats[(i + j) % len(crit_cats)],
                        'category': crit_cats[(i + j) % len(crit_cats)],
                        'max_score': 10.0})

    # ---------------- ความพึงพอใจลูกค้า ----------------
    surveys = []
    if ctx.has('od19.iso.customer.satisfaction') and customers:
        methods = ['questionnaire', 'interview', 'meeting', 'online', 'other']
        sstatus = ['draft', 'sent', 'completed', 'completed']
        for i in range(10):
            vals = {
                'name': 'CSAT-%03d' % (i + 1),
                'partner_id': customers[i % len(customers)].id,
                'date': _d(-75 + i * 7),
                'method': methods[i % len(methods)],
                'status': sstatus[i % len(sstatus)],
            }
            rec = ctx.upsert('od19.iso.customer.satisfaction', 'csat_%02d' % (i + 1), vals)
            if rec:
                surveys.append(rec)
        ctx.log("ความพึงพอใจลูกค้า: %d" % len(surveys))

        if ctx.has('od19.iso.csat.item') and surveys:
            icate = ['quality', 'delivery', 'price', 'service', 'support']
            for i, s in enumerate(surveys):
                for j in range(2):
                    ctx.upsert('od19.iso.csat.item', 'citem_%02d_%d' % (i + 1, j + 1), {
                        'survey_id': s.id,
                        'name': 'หัวข้อประเมิน %s' % icate[(i + j) % len(icate)],
                        'category': icate[(i + j) % len(icate)],
                        'max_score': 5.0})

    # ---------------- ทบทวนของฝ่ายบริหาร ----------------
    if ctx.has('od19.iso.management.review'):
        rstates = ['draft', 'planned', 'in_progress', 'reviewed', 'closed']
        chairman = ctx.user_admin()  # chairman_id เป็น res.users (ไม่ใช่ hr.employee)
        for i in range(5):
            ctx.upsert('od19.iso.management.review', 'mr_%02d' % (i + 1), {
                'name': 'MR-%03d' % (i + 1),
                'title': 'การทบทวนของฝ่ายบริหาร ครั้งที่ %d' % (i + 1),
                'state': rstates[i % len(rstates)],
                'date': _d(-45 + i * 20),
                'chairman_id': chairman.id})
        ctx.log("ทบทวนของฝ่ายบริหาร: 5")

    # ---------------- สมรรถนะ ----------------
    if ctx.has('od19.iso.competence'):
        for i in range(10):
            ctx.upsert('od19.iso.competence', 'comp_%02d' % (i + 1), {
                'name': 'สมรรถนะที่ต้องการ ลำดับ %02d' % (i + 1),
                'category': ['technical', 'managerial', 'quality', 'environment', 'safety', 'iso'][i % 6]})
        ctx.log("สมรรถนะ: 10")

# -*- coding: utf-8 -*-
"""s95_misc — เติมข้อมูลในส่วนที่ยังว่างของ Odoo 19

ครอบคลุม: ราคาขาย (pricelist), ปฏิทินนัดหมาย, บัญชีธนาคารคู่ค้า, ล็อตสินค้า,
ใบขอซื้อ/ข้อตกลงซื้อ, สัญญาซื้อขายล่วงหน้า (blanket order), หมุดหมาย/รายงาน
ความคืบหน้าโครงการ, ยานพาหนะ, ใบนำฝากเช็ค, เอกสารเซ็น, ทักษะพนักงาน (ISO),
ใบสมัครงาน, อัตราแลกเปลี่ยน, ใบวางบิล (billing), รายงาน Money In, แบล็กลิสต์เบอร์โทร

หลักการเดิม: เขียนผ่าน ORM, ผูก External ID, รันซ้ำได้ไม่เกิดข้อมูลซ้ำ
"""
import datetime

import seed_common


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def _dt(offset=0, hour=9, minute=0):
    return (datetime.datetime.now() + datetime.timedelta(days=offset)).replace(
        hour=hour, minute=minute, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')


def _year():
    return datetime.date.today().year


_PRICELISTS = [
    ('pl_01', 'ราคาขายปลีก (Retail)'),
    ('pl_02', 'ราคาขายส่ง (Wholesale)'),
    ('pl_03', 'ราคาโครงการ (Project)'),
    ('pl_04', 'ราคาลูกค้า VIP'),
]

_EVENTS = [
    'ประชุมทีมขายประจำสัปดาห์', 'นัดติดตั้งหน้างานลูกค้า', 'ประชุมวางแผนโครงการ',
    'สัมมนาลูกค้าองค์กร', 'ตรวจรับงานส่งมอบ', 'ประชุมงบประมาณรายไตรมาส',
    'นัดพบซัพพลายเออร์', 'อบรมพนักงานภายใน', 'ประชุมคณะกรรมการบริหาร', 'ติดตามลูกหนี้คงค้าง',
]

_APPLICANTS = [
    'สมชาย ใจดี', 'สมหญิง รักงาน', 'วิชัย ขยัน', 'มาลี สวยงาม', 'ประเสริฐ ตั้งใจ',
    'อรทัย เก่งกาจ', 'ธนากร มีสุข', 'ปิยะ รอบคอบ', 'ศิริพร อดทน', 'ณัฐพล ฉลาด',
]


def run(ctx):
    ctx.step('s95_misc', 'เติมข้อมูลส่วนที่ยังว่าง (pricelist/ปฏิทิน/ธนาคาร/ล็อต/จัดซื้อ/ยานพาหนะ/ฯลฯ)')

    customers = ctx.state.get('customers') or list(
        ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    products = ctx.state.get('products') or list(ctx.find('product.template', [], limit=12))
    variants = [p.product_variant_id for p in products if p.product_variant_id]
    employees = ctx.state.get('employees') or list(ctx.find('hr.employee', [], limit=10))
    projects = list(ctx.find('project.project', [], limit=10))
    partners = list(customers) or list(ctx.find('res.partner', [('is_company', '=', True)], limit=10))

    def cust(i):
        return partners[i % len(partners)] if partners else None

    def var(i):
        return variants[i % len(variants)] if variants else None

    def emp(i):
        return employees[i % len(employees)] if employees else None

    # ------------------------------------------------------- ราคาขาย (pricelist)
    pricelists = []
    if ctx.has('product.pricelist'):
        for key, name in _PRICELISTS:
            rec = ctx.upsert('product.pricelist', key, {
                'name': name,
                'currency_id': ctx.thb.id,
                'company_id': ctx.company.id,
            })
            if rec:
                pricelists.append(rec)
        ctx.log("ราคาขาย (pricelist): %d" % len(pricelists))

    if ctx.has('product.pricelist.item') and pricelists:
        made = 0
        for i in range(10):
            pl = pricelists[i % len(pricelists)]
            vals = {
                'pricelist_id': pl.id,
                'applied_on': '3_global' if i % 2 == 0 else '1_product',
                'base': 'list_price',
                'compute_price': 'percentage' if i % 3 == 0 else 'fixed',
                'min_quantity': 1 + (i % 5),
            }
            if i % 3 == 0:
                vals['percent_price'] = 5.0 + i
            else:
                vals['fixed_price'] = 1000.0 + i * 250
            if i % 2 != 0:
                tmpl = products[i % len(products)] if products else None
                if tmpl:
                    vals['product_tmpl_id'] = tmpl.id
            if ctx.upsert('product.pricelist.item', 'pli_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายการราคา: %d" % made)

    # ------------------------------------------------------------ ปฏิทินนัดหมาย
    if ctx.has('calendar.event'):
        organizer = ctx.user_admin()
        made = 0
        for i in range(10):
            vals = {
                'name': _EVENTS[i],
                'start': _dt(1 + i, 9),
                'stop': _dt(1 + i, 10, 30),
                'show_as': 'busy',
                'privacy': 'public',
                'user_id': organizer.id,
                'location': 'ห้องประชุมใหญ่' if i % 2 == 0 else 'ออนไลน์ (Google Meet)',
            }
            if ctx.upsert('calendar.event', 'evt_%02d' % (i + 1), vals):
                made += 1
        ctx.log("นัดหมายในปฏิทิน: %d" % made)

    # --------------------------------------------------- บัญชีธนาคารของคู่ค้า
    if ctx.has('res.partner.bank'):
        bank = ctx.find('res.bank', [], limit=1)
        made = 0
        for i in range(10):
            p = cust(i) or ctx.company.partner_id
            bank_names = ['KBANK', 'SCB', 'BBL', 'KTB', 'TMB', 'BAY', 'GSB', 'CIMB', 'TTB', 'UOB']
            vals = {
                'acc_number': '%s-%03d-1-%05d-%d' % (bank_names[i % 10], i + 1, 10000 + i, i % 10),
                'partner_id': p.id,
                'currency_id': ctx.thb.id,
            }
            if bank:
                vals['bank_id'] = bank.id
            if ctx.upsert('res.partner.bank', 'pbank_%02d' % (i + 1), vals):
                made += 1
        ctx.log("บัญชีธนาคารคู่ค้า: %d" % made)

    # ----------------------------------------------------------- ล็อตสินค้า
    if ctx.has('stock.lot'):
        storable = [p for p in products
                    if p.type != 'service' and getattr(p, 'is_storable', False)]
        made = 0
        ym = datetime.date.today().strftime('%y%m')
        for i in range(10):
            tmpl = storable[i % len(storable)] if storable else None
            if not tmpl:
                break
            vals = {
                'name': 'LOT-%s-%03d' % (ym, i + 1),
                'product_id': tmpl.product_variant_id.id,
                'company_id': ctx.company.id,
            }
            if ctx.upsert('stock.lot', 'lot_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ล็อต/หมายเลขเครื่อง: %d" % made)

    # ------------------------------------------------------------ ใบขอซื้อ (PR)
    ptype = (ctx.find('stock.picking.type', [('code', '=', 'incoming')], limit=1)
             or ctx.find('stock.picking.type', [], limit=1))
    pr_requests = []
    if ctx.has('purchase.request'):
        requester = ctx.user_admin()
        for i in range(10):
            vals = {
                'name': 'PR-SEED-%04d' % (i + 1),
                'od19_priority': ['normal', 'urgent', 'emergency'][i % 3],
                'picking_type_id': ptype.id if ptype else False,
                'requested_by': requester.id,
                'company_id': ctx.company.id,
                'state': 'draft',
                'date_start': _d(-10 + i),
                'description': '<p>รายละเอียดใบขอซื้อทดสอบ ลำดับ %02d</p>' % (i + 1),
            }
            if vals['od19_priority'] != 'normal':
                vals['od19_request_reason'] = 'เหตุผลความจำเป็นเร่งด่วน (seed)'
            rec = ctx.upsert('purchase.request', 'preq_%02d' % (i + 1), vals)
            if rec:
                pr_requests.append(rec)
        ctx.log("ใบขอซื้อ (PR): %d" % len(pr_requests))

    if ctx.has('purchase.request.line') and pr_requests:
        made = 0
        for i in range(10):
            req = pr_requests[i % len(pr_requests)]
            v = var(i)
            vals = {
                'name': 'รายการขอซื้อ ลำดับ %02d' % (i + 1),
                'request_id': req.id,
                'product_id': v.id if v else False,
                'product_qty': 1 + i,
                'date_required': _d(5 + i),
                'company_id': ctx.company.id,
            }
            if ctx.upsert('purchase.request.line', 'preqline_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายการใบขอซื้อ: %d" % made)

    # ------------------------------------------------- ข้อตกลงซื้อ (requisition)
    requisitions = []
    if ctx.has('purchase.requisition'):
        for i in range(10):
            # od19_approval_state เปลี่ยนได้ผ่าน action เท่านั้น จึงปล่อย default (draft)
            vals = {
                'name': 'PA-SEED-%04d' % (i + 1),
                'company_id': ctx.company.id,
                'od19_entry_mode': 'requisition',
                'requisition_type': 'blanket_order',
                'picking_type_id': ptype.id if ptype else False,
                'state': 'draft',
                'date_start': _d(-30),
                'date_end': _d(60),
                'user_id': ctx.user_admin().id,
            }
            rec = ctx.upsert('purchase.requisition', 'prequisition_%02d' % (i + 1), vals)
            if rec:
                requisitions.append(rec)
        ctx.log("ข้อตกลงซื้อ (requisition): %d" % len(requisitions))

    if ctx.has('purchase.requisition.line') and requisitions:
        made = 0
        for i in range(10):
            req = requisitions[i % len(requisitions)]
            v = var(i)
            vals = {
                'requisition_id': req.id,
                'product_id': v.id if v else False,
                'product_qty': 2 + i,
                'price_unit': (v.standard_price or 100.0) if v else 100.0,
                'company_id': ctx.company.id,
            }
            if ctx.upsert('purchase.requisition.line', 'preqline2_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายการข้อตกลงซื้อ: %d" % made)

    # ตั้งสถานะอนุมัติผ่าน action อย่างเป็นทางการ (idempotent) เพื่อให้มีตัวอย่างหลายสถานะ
    if requisitions:
        submitted = 0
        for i, rec in enumerate(requisitions):
            if i % 3 == 1 and rec.od19_approval_state == 'draft':
                rec.action_od19_submit_for_approval()
                submitted += 1
        ctx.log("ข้อตกลงซื้อที่ส่งขออนุมัติ: %d" % submitted)

    # ------------------------------------------- สัญญาซื้อขายล่วงหน้า (blanket)
    blankets = []
    if ctx.has('sale.blanket.order') and pricelists:
        for i in range(10):
            p = cust(i)
            vals = {
                'partner_id': p.id if p else False,
                'pricelist_id': pricelists[i % len(pricelists)].id,
                'company_id': ctx.company.id,
                'user_id': ctx.user_admin().id,
                'validity_date': _d(90 + i),
                'note': 'สัญญาซื้อขายล่วงหน้าทดสอบ ลำดับ %02d (seed)' % (i + 1),
            }
            rec = ctx.upsert('sale.blanket.order', 'bo_%02d' % (i + 1), vals)
            if rec:
                blankets.append(rec)
        ctx.log("สัญญาซื้อขายล่วงหน้า: %d" % len(blankets))

    if ctx.has('sale.blanket.order.line') and blankets:
        made = 0
        for i in range(10):
            order = blankets[i % len(blankets)]
            v = var(i)
            # constraint ของ OCA บังคับให้มีทั้ง product_id และ product_uom
            if not v:
                continue
            vals = {
                'order_id': order.id,
                'product_id': v.id,
                'product_uom': v.uom_id.id,
                'name': v.display_name,
                'price_unit': v.list_price or 100.0,
                'original_uom_qty': 5 + i,
                'company_id': ctx.company.id,
            }
            if ctx.upsert('sale.blanket.order.line', 'boline_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายการสัญญาซื้อขายล่วงหน้า: %d" % made)

    # ------------------------------------------- หมุดหมายและรายงานความคืบหน้า
    if ctx.has('project.milestone') and projects:
        made = 0
        for i in range(10):
            proj = projects[i % len(projects)]
            vals = {
                'name': 'หมุดหมายที่ %02d — ส่งมอบงวด %d' % (i + 1, i % 3 + 1),
                'project_id': proj.id,
                'deadline': _d(30 + i * 3),
                'is_reached': i % 4 == 0,
            }
            if ctx.upsert('project.milestone', 'milestone_%02d' % (i + 1), vals):
                made += 1
        ctx.log("หมุดหมายโครงการ: %d" % made)

    if ctx.has('project.update') and projects:
        made = 0
        for i in range(10):
            proj = projects[i % len(projects)]
            vals = {
                'name': 'รายงานความคืบหน้าโครงการ ลำดับ %02d' % (i + 1),
                'project_id': proj.id,
                'status': ['on_track', 'at_risk', 'off_track', 'on_hold', 'done'][i % 5],
                'user_id': ctx.user_admin().id,
                'date': _d(-10 + i),
                'progress': (i % 10) * 10,
                'description': '<p>อัปเดตความคืบหน้าโครงการ (seed) ลำดับ %02d</p>' % (i + 1),
            }
            if ctx.upsert('project.update', 'pupdate_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายงานความคืบหน้าโครงการ: %d" % made)

    # ------------------------------------------------------------- ยานพาหนะ
    vehicles_models = []
    if ctx.has('fleet.vehicle.model'):
        brands = list(ctx.find('fleet.vehicle.model.brand', [], limit=10))
        for i in range(10):
            brand = brands[i % len(brands)] if brands else None
            vals = {
                'name': 'รุ่นทดสอบ %02d' % (i + 1),
                'brand_id': brand.id if brand else False,
                'vehicle_type': 'car',
                'power_unit': 'power',
                'range_unit': 'km',
                'transmission': 'automatic',
                'seats': 5,
            }
            rec = ctx.upsert('fleet.vehicle.model', 'fmodel_%02d' % (i + 1), vals)
            if rec:
                vehicles_models.append(rec)
        ctx.log("รุ่นยานพาหนะ: %d" % len(vehicles_models))

    if ctx.has('fleet.vehicle') and vehicles_models:
        made = 0
        prefixes = ['กข', 'กค', 'กง', 'กจ', 'กช', 'ฎ', 'ฑ', 'ฒ', 'ณ', 'ด']
        for i in range(10):
            model = vehicles_models[i % len(vehicles_models)]
            driver = cust(i)
            vals = {
                'model_id': model.id,
                'license_plate': '%s-%04d' % (prefixes[i % 10], 1000 + i),
                'odometer_unit': 'kilometers',
                'power_unit': 'power',
                'odometer': 10000.0 + i * 500,
                'car_value': 750000.0 + i * 25000,
                'company_id': ctx.company.id,
                'driver_id': driver.id if driver else False,
            }
            if ctx.upsert('fleet.vehicle', 'vehicle_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ยานพาหนะ: %d" % made)

    # ------------------------------------------------------ ใบนำฝากเช็ค
    if ctx.has('account.check.deposit'):
        bank_journal = ctx.find('account.journal', [('type', '=', 'bank')], limit=1)
        misc_journal = (ctx.find('account.journal', [('type', '=', 'general')], limit=1)
                        or bank_journal)
        if bank_journal and misc_journal:
            made = 0
            for i in range(10):
                vals = {
                    'journal_id': misc_journal.id,
                    'bank_journal_id': bank_journal.id,
                    'deposit_date': _d(-20 + i * 2),
                    'company_id': ctx.company.id,
                    'state': 'draft',
                }
                if ctx.upsert('account.check.deposit', 'chkdep_%02d' % (i + 1), vals):
                    made += 1
            ctx.log("ใบนำฝากเช็ค: %d" % made)
        else:
            ctx.warn("ไม่พบสมุดรายวันธนาคาร — ข้ามใบนำฝากเช็ค")

    # -------------------------------------------------------- เอกสารเซ็น
    doc_templates = []
    if ctx.has('od19.document.template'):
        tmpls = [
            ('สัญญาจ้างบริการ', 'เทมเพลตสัญญาจ้างบริการ (seed)'),
            ('ใบเสนอราคา', 'เทมเพลตใบเสนอราคา (seed)'),
            ('หนังสือรับรองการหักภาษี ณ ที่จ่าย', 'เทมเพลตหนังสือรับรอง 50 ทวิ (seed)'),
            ('ใบส่งมอบงาน', 'เทมเพลตใบส่งมอบงาน (seed)'),
        ]
        for i, (nm, desc) in enumerate(tmpls):
            rec = ctx.upsert('od19.document.template', 'dtmpl_%02d' % (i + 1), {
                'name': nm,
                'description': desc,
                'body_html': '<p>%s</p>' % desc,
                'company_id': ctx.company.id,
            })
            if rec:
                doc_templates.append(rec)
        ctx.log("เทมเพลตเอกสารเซ็น: %d" % len(doc_templates))

    if ctx.has('od19.document') and doc_templates:
        made = 0
        for i in range(10):
            tmpl = doc_templates[i % len(doc_templates)]
            p = cust(i)
            vals = {
                'template_id': tmpl.id,
                'reference': 'DOC-SEED-%04d' % (i + 1),
                'partner_id': p.id if p else False,
                'body_html': '<p>เนื้อหาเอกสารทดสอบ ลำดับ %02d</p>' % (i + 1),
                'date_deadline': _dt(10 + i, 17),
                'state': ['draft', 'sent', 'signed'][i % 3],
                'user_id': ctx.user_admin().id,
                'company_id': ctx.company.id,
            }
            rec = ctx.upsert('od19.document', 'doc_%02d' % (i + 1), vals)
            if rec:
                made += 1
                if ctx.has('od19.document.signer'):
                    ctx.upsert('od19.document.signer', 'docsigner_%02d' % (i + 1), {
                        'document_id': rec.id,
                        'role_name': ['ผู้มีอำนาจลงนาม', 'ผู้อนุมัติ', 'พยาน'][i % 3],
                        'partner_id': p.id if p else False,
                        'sequence': 10,
                    })
        ctx.log("เอกสารเซ็น: %d" % made)

    # ------------------------------------------------------ ทักษะพนักงาน (ISO)
    if ctx.has('od19.iso.employee.competence') and employees:
        comps = list(ctx.find('od19.iso.competence', [], limit=10))
        made = 0
        if comps:
            for i in range(10):
                e = emp(i)
                vals = {
                    'employee_id': e.id if e else False,
                    'competence_id': comps[i % len(comps)].id,
                    'level': str(i % 5 + 1),
                }
                if ctx.upsert('od19.iso.employee.competence', 'empcomp_%02d' % (i + 1), vals):
                    made += 1
        ctx.log("ทักษะพนักงาน (ISO): %d" % made)

    # ---------------------------------------------------------- ใบสมัครงาน
    if ctx.has('od19.job.application'):
        jobs = list(ctx.find('od19.job.opening', [], limit=10))
        made = 0
        if jobs:
            for i in range(10):
                vals = {
                    'job_id': jobs[i % len(jobs)].id,
                    'name': _APPLICANTS[i],
                    'email': 'applicant%02d@example.com' % (i + 1),
                    'state': ['new', 'shortlisted', 'interview', 'offer', 'hired', 'refused'][i % 6],
                }
                if ctx.upsert('od19.job.application', 'jobapp_%02d' % (i + 1), vals):
                    made += 1
        ctx.log("ใบสมัครงาน: %d" % made)

    # ---------------------------------------------------------- อัตราแลกเปลี่ยน
    foreign = []
    if ctx.has('res.currency'):
        for code in ['USD', 'EUR', 'CNY', 'JPY', 'GBP']:
            cur = ctx.find('res.currency', [('name', '=', code)], limit=1)
            if cur:
                foreign.append(cur)
    if ctx.has('res.currency.rate') and foreign:
        # rate = มูลค่าของ 1 หน่วยสกุลเงินบริษัท (THB) เมื่อเทียบกับสกุลต่างประเทศ
        thb_per_unit = {'USD': 34.50, 'EUR': 37.20, 'CNY': 4.86, 'JPY': 0.2320, 'GBP': 43.90}
        year = _year()
        made = 0
        for idx, cur in enumerate(foreign):
            for j, day in enumerate(('%d-01-01' % year, '%d-07-01' % year)):
                rate = round(1.0 / thb_per_unit.get(cur.name, 1.0), 6)
                vals = {
                    'currency_id': cur.id,
                    'name': day,
                    'rate': rate,
                    'company_id': ctx.company.id,
                }
                if ctx.upsert('res.currency.rate', 'rate_%02d_%d' % (idx + 1, j + 1), vals):
                    made += 1
        ctx.log("อัตราแลกเปลี่ยน: %d" % made)

    # --------------------------------------------- แหล่งอัตราแลกเปลี่ยนอัตโนมัติ
    if ctx.has('res.currency.rate.provider') and foreign:
        sel = ctx.fields('res.currency.rate.provider').get('service')
        codes = []
        if sel is not None and isinstance(sel.selection, list):
            codes = [s[0] for s in sel.selection if s[0] != 'none']
        if codes:
            ctx.upsert('res.currency.rate.provider', 'crp_01', {
                'service': codes[0],
                'currency_ids': [(6, 0, [c.id for c in foreign])],
                'company_id': ctx.company.id,
                'interval_number': 1,
                'interval_type': 'days',
                'next_run': _d(1),
            })
            ctx.log("แหล่งอัตราแลกเปลี่ยนอัตโนมัติ: 1")

    # -------------------------------------------------------- ใบวางบิล (billing)
    if ctx.has('account.billing'):
        made = 0
        for i in range(10):
            p = cust(i)
            vals = {
                'partner_id': p.id if p else False,
                'currency_id': ctx.thb.id,
                'company_id': ctx.company.id,
                'date': _d(-25 + i * 2),
                'threshold_date': _d(-10 + i * 2),
                'threshold_date_type': ['invoice_date_due', 'invoice_date'][i % 2],
                'state': 'draft',
            }
            if ctx.upsert('account.billing', 'billing_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบวางบิล: %d" % made)

    # ----------------------------------------------------- รายงาน Money In
    if ctx.has('od19.money.in.report.run'):
        year = _year()
        quarters = [('01-01', '03-31'), ('04-01', '06-30'),
                    ('07-01', '09-30'), ('10-01', '12-31')]
        made = 0
        for i in range(10):
            q_start, q_end = quarters[i % 4]
            vals = {
                'name': 'MIR-%d-%02d' % (year, i + 1),
                'company_id': ctx.company.id,
                'date_from': '%d-%s' % (year, q_start),
                'date_to': '%d-%s' % (year, q_end),
                'phase': ['phase1_invoice_based', 'phase2_cash_invoice_based'][i % 2],
                'generated_by': ctx.user_admin().id,
                'generated_at': '%d-%s 09:00:00' % (year, q_start),
                'status': 'draft',
                'job_type_values': ['job', 'pm', 'service', 'sale', 'unknown'][i % 5],
                'notes': 'รายงานวิเคราะห์เงินเข้า (seed) ลำดับ %02d' % (i + 1),
            }
            if ctx.upsert('od19.money.in.report.run', 'mirr_%02d' % (i + 1), vals):
                made += 1
        ctx.log("รายงาน Money In: %d" % made)

    # ------------------------------------------------------ แบล็กลิสต์เบอร์โทร
    if ctx.has('phone.blacklist'):
        made = 0
        for i in range(10):
            vals = {
                'number': '+668%08d' % (10000000 + i * 111),
                'active': True,
            }
            if ctx.upsert('phone.blacklist', 'blacklist_%02d' % (i + 1), vals):
                made += 1
        ctx.log("แบล็กลิสต์เบอร์โทร: %d" % made)

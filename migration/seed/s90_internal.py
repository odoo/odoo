# -*- coding: utf-8 -*-
"""s90_internal — เครื่องมือภายในและส่วนที่เหลือของ od19_* (ประกาศ ห้องประชุม ยืมทรัพย์สิน
QC ขนส่ง คืนสินค้า ใบรับบริการ เคลมประกัน สัญญาขาย เงื่อนไขซื้อขาย ฯลฯ)
"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def _dt(offset=0, hour=9):
    return (datetime.datetime.now() + datetime.timedelta(days=offset)).replace(
        hour=hour, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')


_TITLES = ['แอร์', 'เครื่องทำความเย็น', 'คอมเพรสเซอร์', 'พัดลม', 'น้ำยาแอร์', 'แผงวงจร',
           'ท่อทองแดง', 'รีโมท', 'เซนเซอร์', 'มอเตอร์']


def run(ctx):
    ctx.step('s90_internal', 'เครื่องมือภายในและโมดูล od19_* ที่เหลือ')
    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    vendors = ctx.state.get('vendors') or list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))
    products = ctx.state.get('products') or list(ctx.find('product.template', [], limit=12))
    employees = ctx.state.get('employees') or list(ctx.find('hr.employee', [], limit=10))
    projects = list(ctx.find('project.project', [], limit=10))

    def prod(i):
        return products[i % len(products)] if products else None

    def cust(i):
        return customers[i % len(customers)] if customers else None

    def vend(i):
        return vendors[i % len(vendors)] if vendors else None

    def emp(i):
        return employees[i % len(employees)] if employees else None

    # ---------------- ประกาศ ----------------
    if ctx.has('announcement'):
        atypes = ['info', 'warning', 'mandatory']
        for i in range(10):
            ctx.upsert('announcement', 'ann_%02d' % (i + 1), {
                'name': 'ประกาศภายใน ลำดับ %02d' % (i + 1),
                'body': '<p>เนื้อหาประกาศทดสอบ (seed) ลำดับ %d</p>' % (i + 1),
                'announcement_type': atypes[i % len(atypes)],
                'target_type': 'company'})
        ctx.log("ประกาศภายใน: 10")

    # ---------------- งานซ่อมบำรุง ----------------
    equip = []
    if ctx.has('maintenance.equipment'):
        for i in range(10):
            vals = {
                'name': 'อุปกรณ์/เครื่องจักร ลำดับ %02d' % (i + 1),
                'effective_date': _d(-200 + i * 5),
                'equipment_assign_to': ['department', 'employee', 'other'][i % 3],
            }
            rec = ctx.upsert('maintenance.equipment', 'maint_eq_%02d' % (i + 1), vals)
            if rec:
                equip.append(rec)
        ctx.log("อุปกรณ์ซ่อมบำรุง: %d" % len(equip))

    if ctx.has('maintenance.request') and equip:
        made = 0
        for i in range(10):
            vals = {
                'name': 'ใบแจ้งซ่อมบำรุง ลำดับ %02d' % (i + 1),
                'company_id': ctx.company.id,
                'kanban_state': ['normal', 'blocked', 'done'][i % 3],
                'equipment_id': equip[i % len(equip)].id,
                'request_date': _d(-30 + i * 3),
            }
            if ctx.upsert('maintenance.request', 'mreq_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบแจ้งซ่อม: %d" % made)

    # ---------------- ยืมทรัพย์สิน ----------------
    if ctx.has('asset.loan'):
        loans = []
        fallback_partner = ctx.company.partner_id  # borrower_id เป็น res.partner
        for i in range(10):
            borrower = cust(i) or fallback_partner
            vals = {
                'name': 'LOAN-%04d' % (i + 1),
                'borrower_id': borrower.id,
                'loan_date': _d(-25 + i * 2),
                'state': ['draft', 'borrowed', 'returned'][i % 3],
                'company_id': ctx.company.id,
            }
            rec = ctx.upsert('asset.loan', 'loan_%02d' % (i + 1), vals)
            if rec:
                loans.append(rec)
        ctx.log("การยืมทรัพย์สิน: %d" % len(loans))

        if ctx.has('asset.loan.line') and loans and equip:
            for i, ln in enumerate(loans):
                ctx.upsert('asset.loan.line', 'loan_line_%02d' % (i + 1), {
                    'loan_id': ln.id, 'equipment_id': equip[i % len(equip)].id, 'quantity': 1})

    # ---------------- ห้องประชุม ----------------
    rooms = []
    if ctx.has('od19.meeting.room'):
        for i, (name, cap) in enumerate([('ห้องประชุมใหญ่', 20),
                                         ('ห้องประชุมเล็ก', 8),
                                         ('ห้องประชุมชั้น 2', 12)]):
            rec = ctx.upsert('od19.meeting.room', 'room_%02d' % (i + 1),
                             {'name': name, 'company_id': ctx.company.id,
                              'capacity': cap})
            if rec:
                rooms.append(rec)

    if ctx.has('od19.meeting.room.booking') and rooms:
        made = 0
        organizer = ctx.user_admin()  # organizer_id เป็น res.users
        for i in range(10):
            vals = {
                'reference': 'BK-%04d' % (i + 1),
                'name': 'การจองห้องประชุม ลำดับ %02d' % (i + 1),
                'room_id': rooms[i % len(rooms)].id,
                'organizer_id': organizer.id,
                'start_datetime': _dt(1 + i, 9),
                'end_datetime': _dt(1 + i, 11),
                'state': ['booked', 'in_use', 'done'][i % 3],
                'company_id': ctx.company.id,
            }
            if ctx.upsert('od19.meeting.room.booking', 'booking_%02d' % (i + 1), vals):
                made += 1
        ctx.log("การจองห้องประชุม: %d" % made)

    # ---------------- QC Inspection ----------------
    if ctx.has('od19.qc.inspection') and products:
        made = 0
        for i in range(10):
            vals = {
                'name': 'QC-%04d' % (i + 1),
                'company_id': ctx.company.id,
                'inspection_type': ['incoming', 'outgoing', 'in_process'][i % 3],
                'product_id': prod(i).product_variant_id.id,
                'qty_tested': 10.0 + i,
                'inspection_date': _d(-20 + i * 2),
                'state': ['draft', 'in_progress', 'passed', 'failed'][i % 4],
            }
            rec = ctx.upsert('od19.qc.inspection', 'qc_%02d' % (i + 1), vals)
            if rec:
                made += 1
                if ctx.has('od19.qc.inspection.line'):
                    ctx.upsert('od19.qc.inspection.line', 'qcline_%02d' % (i + 1), {
                        'inspection_id': rec.id,
                        'parameter': 'พารามิเตอร์ตรวจสอบ %02d' % (i + 1),
                        'result': 'pass' if i % 3 else 'fail'})
        ctx.log("การตรวจ QC: %d" % made)

    # ---------------- ขนส่ง ----------------
    if ctx.has('od19.transport.order'):
        made = 0
        for i in range(10):
            vals = {
                'date': _d(-20 + i * 2),
                'origin_location': 'คลังสินค้าสำนักงานใหญ่ (กรุงเทพฯ)',
                'destination_location': ['ระยอง', 'ชลบุรี', 'เชียงใหม่', 'สงขลา', 'อุดรธานี'][i % 5],
                'state': ['draft', 'confirmed', 'in_transit', 'delivered'][i % 4],
            }
            if ctx.upsert('od19.transport.order', 'transport_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบสั่งขนส่ง: %d" % made)

    # ---------------- คืนสินค้า ----------------
    if ctx.has('od19.product.return') and products:
        made = 0
        for i in range(10):
            vals = {
                'partner_id': cust(i).id if cust(i) else False,
                'product_id': prod(i).product_variant_id.id,
                'quantity': 1.0 + (i % 3),
                'reason': ['defective', 'wrong_product', 'damaged', 'not_as_described', 'warranty', 'other'][i % 6],
                'return_date': _d(-15 + i),
                'state': ['draft', 'confirmed', 'approved', 'returned', 'refunded'][i % 5],
            }
            if ctx.upsert('od19.product.return', 'pret_%02d' % (i + 1), vals):
                made += 1
        ctx.log("การคืนสินค้า: %d" % made)

    # ---------------- ใบรับบริการ (Service Card) ----------------
    if ctx.has('od19.service.card') and products:
        made = 0
        for i in range(10):
            vals = {
                'name': 'SVC-%04d' % (i + 1),
                'company_id': ctx.company.id,
                'partner_id': cust(i).id if cust(i) else False,
                'product_id': prod(i).product_variant_id.id,
                'service_date': _d(-40 + i * 3),
                'service_type': ['preventive', 'corrective', 'inspection', 'installation', 'other'][i % 5],
            }
            if ctx.upsert('od19.service.card', 'svc_%02d' % (i + 1), vals):
                made += 1
        ctx.log("ใบรับบริการ: %d" % made)

    # ---------------- เคลมประกัน ----------------
    if ctx.has('od19.warranty.claim') and products:
        made = 0
        for i in range(10):
            vals = {
                'name': 'WC-%04d' % (i + 1),
                'company_id': ctx.company.id,
                'partner_id': cust(i).id if cust(i) else False,
                'product_id': prod(i).product_variant_id.id,
                'claim_date': _d(-35 + i * 3),
                'claim_type': ['warranty', 'rma', 'repair'][i % 3],
                'description': 'รายละเอียดการเคลมทดสอบ ลำดับ %02d' % (i + 1),
            }
            if ctx.upsert('od19.warranty.claim', 'wclaim_%02d' % (i + 1), vals):
                made += 1
        ctx.log("เคลมประกัน: %d" % made)

    # ---------------- สัญญาขาย ----------------
    if ctx.has('od19.sales.contract'):
        made = 0
        for i in range(5):
            proj = projects[i % len(projects)] if projects else None
            vals = {
                'name': 'SC-%04d' % (i + 1),
                'partner_id': cust(i).id if cust(i) else False,
                'od19_project_id': proj.id if proj else False,
                'state': ['draft', 'approved', 'active', 'active', 'closed'][i],
                'limit_amount': 500000.0 + i * 250000,
                'over_limit_policy': ['warn', 'approval', 'block'][i % 3],
            }
            if ctx.upsert('od19.sales.contract', 'scontract_%02d' % (i + 1), vals):
                made += 1
        ctx.log("สัญญาขาย: %d" % made)

    # ---------------- เงื่อนไขการซื้อขาย (Template) ----------------
    if ctx.has('od19.sale.term.template'):
        for i, tt in enumerate(['price', 'delivery', 'payment_product', 'payment_engineering',
                                'validity', 'warranty', 'credit']):
            ctx.upsert('od19.sale.term.template', 'sterm_%02d' % (i + 1), {
                'name': 'เงื่อนไขการขาย: %s' % tt, 'term_type': tt,
                'description': '<p>รายละเอียดเงื่อนไข %s (seed)</p>' % tt})
        ctx.log("เทมเพลตเงื่อนไขการขาย: 7")

    if ctx.has('od19.purchase.term.template'):
        for i, tt in enumerate(['warranty', 'delivery_to', 'payment_term', 'shipment', 'weight']):
            ctx.upsert('od19.purchase.term.template', 'pterm_%02d' % (i + 1), {
                'name': 'เงื่อนไขการซื้อ: %s' % tt, 'term_type': tt,
                'description': '<p>รายละเอียดเงื่อนไข %s (seed)</p>' % tt})
        ctx.log("เทมเพลตเงื่อนไขการซื้อ: 5")

    # ---------------- ประเภท / หมวด ต่าง ๆ ----------------
    if ctx.has('od19.goods.issue.type'):
        for i, n in enumerate(['สินค้าชำรุด', 'ส่งผิดรุ่น', 'ของหมดสต็อก', 'ลูกค้ายกเลิก', 'อื่น ๆ']):
            ctx.upsert('od19.goods.issue.type', 'git_%02d' % (i + 1), {'name': n})

    if ctx.has('od19.project.type'):
        for i, n in enumerate(['งานโครงการ (Job)', 'งานบำรุงรักษา (PM)', 'งานบริการ (Service)', 'งานขาย (Sale)']):
            ctx.upsert('od19.project.type', 'ptype_%02d' % (i + 1), {'name': n})

    if ctx.has('od19.vehicle.expense.category'):
        for i, et in enumerate(['fuel', 'maintenance', 'insurance', 'registration',
                                'toll', 'washing', 'depreciation', 'other']):
            ctx.upsert('od19.vehicle.expense.category', 'vecat_%02d' % (i + 1), {
                'name': 'ค่าใช้จ่ายรถยนต์: %s' % et, 'expense_type': et})
        ctx.log("หมวดค่าใช้จ่ายรถยนต์: 8")

    # ---------------- Dashboard ----------------
    if ctx.has('od19.dashboard'):
        uid = ctx.user_admin().id
        for i, (aud, dr) in enumerate([('owner', 'this_month'), ('management', 'this_year'),
                                       ('operational', 'last_30_days'), ('management', 'last_7_days'),
                                       ('owner', 'this_quarter')]):
            ctx.upsert('od19.dashboard', 'dash_%02d' % (i + 1), {
                'name': 'แดชบอร์ดทดสอบ ลำดับ %02d' % (i + 1),
                'audience': aud, 'company_id': ctx.company.id,
                'owner_id': uid, 'default_date_range': dr})
        ctx.log("แดชบอร์ด: 5")

    # ---------------- นับสต็อก ----------------
    if ctx.has('od19.stock.count.session'):
        wh = ctx.find('stock.warehouse', [], limit=1)
        loc = wh.lot_stock_id if wh else ctx.find('stock.location', [('usage', '=', 'internal')], limit=1)
        if loc:
            for i in range(3):
                sess = ctx.upsert('od19.stock.count.session', 'scs_%02d' % (i + 1), {
                    'name': 'รอบนับสต็อก %02d' % (i + 1),
                    'location_id': loc.id,
                    'state': ['scheduled', 'counted', 'adjusted'][i]})
                if sess and ctx.has('od19.stock.count.line'):
                    quants = ctx.find('stock.quant', [('location_id', '=', loc.id)], limit=5)
                    for j, q in enumerate(quants):
                        ctx.upsert('od19.stock.count.line', 'scline_%02d_%d' % (i + 1, j + 1), {
                            'session_id': sess.id, 'quant_id': q.id,
                            'system_qty': q.quantity, 'counted_qty': q.quantity})
            ctx.log("รอบนับสต็อก: 3")

    # ---------------- บล็อกเว็บไซต์ (ถ้ามี) ----------------
    if ctx.has('blog.post'):
        blog = ctx.find('blog.blog', [], limit=1)
        if blog:
            for i in range(3):
                ctx.guard('blog/%d' % i, ctx.upsert, 'blog.post', 'blogpost_%02d' % (i + 1), {
                    'name': 'ข่าวสารบริษัท ลำดับ %02d' % (i + 1),
                    'blog_id': blog.id,
                    'subtitle': 'ข่าวประชาสัมพันธ์ (seed)',
                    'content': '<p>เนื้อหาข่าวทดสอบ</p>'})
            ctx.log("โพสต์บล็อก: 3")

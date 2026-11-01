# -*- coding: utf-8 -*-
"""s40_purchase_stock — ใบสั่งซื้อ สต็อกคงเหลือ และการยืนยันออเดอร์"""
import seed_common
import datetime

_PO = [
    ('po_01', 4, 0, 'internal'), ('po_02', 2, 1, 'internal'),
    ('po_03', 6, 2, 'internal'),  ('po_04', 1, 3, 'internal'),
    ('po_05', 10, 4, 'internal'),('po_06', 3, 5, 'internal'),
    ('po_07', 8, 6, 'internal'), ('po_08', 5, 7, 'internal'),
    ('po_09', 2, 0, 'internal'),  ('po_10', 12, 2, 'internal'),
]

_QTY = [50, 30, 100, 20, 80, 45, 60, 25, 15, 70, 40, 55]


def _ensure_runner_department(ctx):
    """เตรียมแผนกที่มีรหัส + ผูกพนักงานกับผู้รัน/ผู้ดูแล

    picking ขาออก (delivery order) บังคับให้มี DEPT (od19_department_code)
    โดยดึงจากแผนกของพนักงานที่ผูกกับผู้ใช้ปัจจุบัน จึงต้องมีแผนกที่มี code
    และพนักงานที่ผูกกับผู้ใช้ก่อนยืนยันใบสั่งขาย
    """
    if not (ctx.has('hr.department') and ctx.has('hr.employee')):
        return
    dept = ctx.upsert('hr.department', 'dept_03', {'name': 'ฝ่ายขาย', 'code': 'SA'})
    if not dept or not dept.code:
        return
    users = []
    for u in (ctx.env.user, ctx.user_admin()):
        if u and u.id and not any(u.id == x.id for x in users):
            users.append(u)
    for u in users:
        emp = ctx.find('hr.employee', [('user_id', '=', u.id)], limit=1)
        if emp:
            if not emp.department_id:
                ctx.guard('empdept/%s' % emp.id, emp.write, {'department_id': dept.id})
        else:
            ctx.upsert('hr.employee', 'emp_user_%s' % u.id,
                       {'name': u.name or 'Seed User',
                        'user_id': u.id, 'department_id': dept.id})


def run(ctx):
    ctx.step('s40_purchase_stock', 'ใบสั่งซื้อและสต็อก')
    vendors = ctx.state.get('vendors') or list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))
    products = ctx.state.get('products') or list(ctx.find('product.template', [], limit=12))

    # ---------------- Purchase Orders ----------------
    pos = []
    if ctx.has('purchase.order') and vendors and products:
        planned = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for i, (key, qty, pidx, purpose) in enumerate(_PO):
            partner = vendors[i % len(vendors)]
            prod = products[pidx % len(products)]
            line = (0, 0, {
                'product_id': prod.product_variant_id.id,
                'name': prod.name,
                'product_qty': qty,
                'price_unit': prod.standard_price or prod.list_price,
                'date_planned': planned,
                'od19_procurement_purpose': purpose,
            })
            vals = {'partner_id': partner.id, 'order_line': [line]}
            rec = ctx.upsert('purchase.order', key, vals)
            if rec:
                pos.append(rec)
        ctx.state['purchase_orders'] = pos
        ctx.log("ใบสั่งซื้อ: %d" % len(pos))
    else:
        ctx.warn('ข้อมูลไม่พอสำหรับใบสั่งซื้อ — ข้าม')

    # ---------------- Stock on hand (quants) ----------------
    if ctx.has('stock.quant') and products:
        wh = ctx.find('stock.warehouse', [], limit=1)
        loc = wh.lot_stock_id if wh else ctx.find('stock.location', [('usage', '=', 'internal')], limit=1)
        if loc:
            made = 0
            for i, prod in enumerate(products):
                # ข้ามสินค้าประเภทบริการ/ไม่เก็บสต็อก (สร้าง quant ไม่ได้)
                if prod.type == 'service' or not getattr(prod, 'is_storable', True):
                    continue
                variant = prod.product_variant_id
                existing = ctx.find('stock.quant', [('product_id', '=', variant.id), ('location_id', '=', loc.id)], limit=1)
                if existing:
                    continue
                qty = _QTY[i % len(_QTY)]
                res = ctx.guard('quant/%s' % variant.id,
                                ctx.env['stock.quant']._update_available_quantity, variant, loc, qty)
                if res is not None:
                    made += 1
            ctx.log("สต็อกคงเหลือ: ตั้งต้น %d รายการ (คลัง %s)" % (made, loc.display_name))
        else:
            ctx.warn('ไม่พบคลังสินค้าภายใน — ข้ามสต็อก')
    else:
        ctx.warn('ไม่มีโมเดล stock.quant — ข้าม')

    # ---------------- ยืนยันบางออเดอร์เพื่อให้เกิด picking ----------------
    # picking ขาออกบังคับ DEPT -> เตรียมแผนก+พนักงานของผู้รันก่อนยืนยัน SO
    _ensure_runner_department(ctx)
    confirmed_so = 0
    for rec in (ctx.state.get('sale_orders') or [])[:3]:
        if rec.state in ('draft', 'sent'):
            if ctx.guard('confirm-so/%s' % rec.id, rec.action_confirm) is not None:
                confirmed_so += 1
    confirmed_po = 0
    for rec in (ctx.state.get('purchase_orders') or [])[:3]:
        if rec.state in ('draft', 'sent', 'to approve'):
            if hasattr(rec, 'button_approve'):
                ctx.guard('approve-po/%s' % rec.id, rec.button_approve)
            if ctx.guard('confirm-po/%s' % rec.id, rec.button_confirm) is not None:
                confirmed_po += 1
    ctx.log("ยืนยันออเดอร์: SO %d / PO %d (เพื่อสร้าง picking)" % (confirmed_so, confirmed_po))

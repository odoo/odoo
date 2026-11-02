# -*- coding: utf-8 -*-
"""s30_crm_sale — CRM (โอกาสขาย) และใบสั่งขาย"""
import seed_common

_LEADS = [
    ('lead_01', 'สนใจระบบปรับอากาศอาคารสำนักงาน', 850000.0, 60),
    ('lead_02', 'ขอใบเสนอราคาเครื่องทำน้ำเย็น', 1200000.0, 40),
    ('lead_03', 'โครงการติดตั้งแอร์โรงงานใหม่', 2500000.0, 50),
    ('lead_04', 'ต้องการสัญญาบำรุงรักษารายปี', 180000.0, 70),
    ('lead_05', 'เปลี่ยนคอมเพรสเซอร์ชุดเก่า', 260000.0, 30),
    ('lead_06', 'สอบถามราคาน้ำยาแอร์จำนวนมาก', 95000.0, 25),
    ('lead_07', 'ขยายระบบแอร์หอผู้ป่วย', 1600000.0, 45),
    ('lead_08', 'ซ่อมบำรุงด่วน (Corrective)', 45000.0, 80),
    ('lead_09', 'โครงการรีสอร์ท จ.เชียงใหม่', 3200000.0, 20),
    ('lead_10', 'จัดหา Installation Kit ประจำปี', 150000.0, 55),
]

_SO = [
    ('so_01', 'one_time', 2, 0),
    ('so_02', 'one_time', 1, 4),
    ('so_03', 'contract', 3, 10),
    ('so_04', 'one_time', 1, 0),
    ('so_05', 'one_time', 2, 2),
    ('so_06', 'contract', 1, 11),
    ('so_07', 'one_time', 4, 5),
    ('so_08', 'one_time', 1, 4),
    ('so_09', 'contract', 2, 2),
    ('so_10', 'one_time', 3, 3),
]


def run(ctx):
    ctx.step('s30_crm_sale', 'CRM และใบสั่งขาย')
    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    products = ctx.state.get('products') or list(ctx.find('product.template', [], limit=12))

    # ---------------- CRM ----------------
    if ctx.has('crm.lead'):
        for i, (key, title, revenue, prob) in enumerate(_LEADS):
            partner = customers[i % len(customers)] if customers else None
            vals = {
                'name': title, 'type': 'opportunity',
                'partner_id': partner.id if partner else False,
                'expected_revenue': revenue, 'probability': prob,
                'description': '<p>ข้อมูลตัวอย่างสำหรับทดสอบ (seed)</p>',
            }
            ctx.upsert('crm.lead', key, vals)
        ctx.log("CRM opportunities: %d" % len(_LEADS))
    else:
        ctx.warn('ไม่มีโมเดล crm.lead — ข้าม')

    # ---------------- Sale Orders ----------------
    if not ctx.has('sale.order'):
        ctx.warn('ไม่มีโมเดล sale.order — ข้าม')
        return
    if not customers or not products:
        ctx.warn('ไม่มีคู่ค้า/สินค้าเพียงพอ — ข้ามการสร้างใบสั่งขาย')
        return

    orders = []
    for i, (key, mode, qty, pidx) in enumerate(_SO):
        partner = customers[i % len(customers)]
        prod = products[pidx % len(products)]
        line = (0, 0, {
            'product_id': prod.product_variant_id.id,
            'name': prod.name,
            'product_uom_qty': qty,
            'price_unit': prod.list_price,
        })
        vals = {
            'partner_id': partner.id,
            'od19_sale_mode': mode,
            'picking_policy': 'direct',
            'order_line': [line],
        }
        rec = ctx.upsert('sale.order', key, vals)
        if rec:
            orders.append(rec)

    ctx.state['sale_orders'] = orders
    ctx.log("ใบสั่งขาย: %d" % len(orders))

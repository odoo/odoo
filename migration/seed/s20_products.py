# -*- coding: utf-8 -*-
"""s20_products — สินค้า/บริการตัวอย่าง"""
import seed_common

# (key, code, name, type, sale_price, cost, is_storable)
_PRODUCTS = [
    ('prod_01', 'ST-1001', 'เครื่องปรับอากาศ อินเวอร์เตอร์ 12000 BTU', 'consu', 25900.0, 19500.0, True),
    ('prod_02', 'ST-1002', 'เครื่องทำน้ำเย็นอุตสาหกรรม 5 ตัน', 'consu', 185000.0, 142000.0, True),
    ('prod_03', 'ST-1003', 'ท่อทองแดง แอร์ 1/4 นิ้ว (ม้วน 15 ม.)', 'consu', 1250.0, 890.0, True),
    ('prod_04', 'ST-1004', 'คอมเพรสเซอร์ แอร์ 24000 BTU', 'consu', 8900.0, 6400.0, True),
    ('prod_05', 'ST-1005', 'น้ำยาแอร์ R32 (ถัง 10 กก.)', 'consu', 3200.0, 2450.0, True),
    ('prod_06', 'ST-1006', 'แผงวงจรควบคุม (Control Board)', 'consu', 4500.0, 3100.0, True),
    ('prod_07', 'ST-1007', 'พัดลมคอยล์เย็น มอเตอร์ DC', 'consu', 2800.0, 1900.0, True),
    ('prod_08', 'ST-1008', 'ชุดติดตั้งแอร์สำเร็จรูป (Installation Kit)', 'consu', 1500.0, 980.0, True),
    ('svc_01', 'SV-2001', 'บริการติดตั้งเครื่องปรับอากาศ', 'service', 2500.0, 0.0, False),
    ('svc_02', 'SV-2002', 'บริการล้างแอร์ (ต่อเครื่อง)', 'service', 800.0, 0.0, False),
    ('svc_03', 'SV-2003', 'บริการบำรุงรักษาตามรอบ (สัญญารายปี)', 'service', 12000.0, 0.0, False),
    ('svc_04', 'SV-2004', 'บริการซ่อมและเปลี่ยนอะไหล่', 'service', 1800.0, 0.0, False),
]


def run(ctx):
    ctx.step('s20_products', 'สินค้า/บริการ')
    if not ctx.has('product.template'):
        ctx.warn('ไม่มีโมเดล product.template — ข้าม')
        return

    uom = ctx.uom('Units') or ctx.uom('Unit') or ctx.find('uom.uom', [], limit=1)
    categ = ctx.find('product.category', [], limit=1)
    tax_sale = ctx.find('account.tax', [('amount', '=', 7.0), ('type_tax_use', '=', 'sale')], limit=1)
    tax_purch = ctx.find('account.tax', [('amount', '=', 7.0), ('type_tax_use', '=', 'purchase')], limit=1)

    products = []
    for key, code, name, ptype, price, cost, storable in _PRODUCTS:
        vals = {
            'name': name, 'type': ptype, 'default_code': code,
            'list_price': price, 'standard_price': cost,
            'uom_id': uom.id if uom else False,
            'categ_id': categ.id if categ else False,
            'sale_ok': True, 'purchase_ok': True,
            'is_storable': storable,
            'taxes_id': [(6, 0, tax_sale.ids)] if tax_sale else False,
            'supplier_taxes_id': [(6, 0, tax_purch.ids)] if tax_purch else False,
        }
        rec = ctx.upsert('product.template', key, vals)
        if rec:
            products.append(rec)

    if not products:
        products = list(ctx.find('product.template', [], limit=12))

    ctx.state['products'] = products
    ctx.log("สินค้า/บริการ %d รายการ" % len(products))

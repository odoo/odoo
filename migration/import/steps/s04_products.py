# -*- coding: utf-8 -*-
"""s04_products — สินค้า/บริการ หมวดหมู่ หน่วยนับ ภาษี และรายการราคา

หลักการ:
    * นำเข้าเฉพาะสินค้าที่ active=true จากระบบเดิม (สอดคล้องกับ s03_partners)
    * หมวดหมู่/หน่วยนับ/ภาษี จับคู่ผ่านไฟล์ mapping CSV ใน migration/mapping
    * ทุก record ผูก External ID __import15__.product_template.<legacy_id>
      จึงรันซ้ำได้โดยไม่เกิดข้อมูลซ้ำ
    * สินค้าบางรายการที่ข้อมูลเดิมไม่ผ่านข้อกำหนดของ Odoo 19 (เช่น barcode ซ้ำ)
      จะถูกบันทึกเป็นข้อผิดพลาดแล้วข้ามไป ไม่ทำให้ทั้งขั้นตอนล้มเหลว
"""
import common
import legacy

# OD15 type -> (OD19 type, is_storable)
_PRODUCT_TYPE = {
    'product': ('consu', True),    # สินค้าคงคลัง (storable)
    'consu': ('consu', False),     # สินค้าสิ้นเปลือง
    'service': ('service', False),
}

# OD15 type_tax_use -> OD19 type_tax_use ('payment' ของเดิมคือ WHT -> purchase)
_TAX_TYPE = {'sale': 'sale', 'purchase': 'purchase', 'payment': 'purchase'}

# อ่านสินค้าจากระบบเดิม: ใช้ค่าจาก variant แรกของแต่ละ template
# (OD15 เก็บ default_code/barcode/standard_price ไว้ที่ product_product)
_PRODUCT_SQL = """
SELECT pt.id AS tmpl_id, pt.name, pt.type, pt.categ_id, pt.uom_id,
       pt.list_price, pt.sale_ok, pt.purchase_ok,
       u.name AS uom_name,
       (SELECT pp.default_code FROM product_product pp
         WHERE pp.product_tmpl_id = pt.id
           AND pp.default_code IS NOT NULL AND pp.default_code <> ''
         ORDER BY pp.id LIMIT 1) AS default_code,
       (SELECT pp.barcode FROM product_product pp
         WHERE pp.product_tmpl_id = pt.id
           AND pp.barcode IS NOT NULL AND pp.barcode <> ''
         ORDER BY pp.id LIMIT 1) AS barcode,
       (SELECT pp.id FROM product_product pp
         WHERE pp.product_tmpl_id = pt.id ORDER BY pp.id LIMIT 1) AS variant_id,
       (SELECT count(*) FROM product_product pp
         WHERE pp.product_tmpl_id = pt.id) AS variant_count
FROM product_template pt
LEFT JOIN uom_uom u ON u.id = pt.uom_id
WHERE pt.active = true
ORDER BY pt.id
"""


def run(stats):
    env = common.odoo_env()
    uoms = _uom_cache(env)
    cats = _category_cache(env)
    taxes = _tax_cache(env)
    _sync_products(env, stats, uoms, cats, taxes)
    _sync_pricelist_items(env, stats, cats)


# --------------------------------------------------------------------------
# cache: หมวดหมู่สินค้า / หน่วยนับ / ภาษี
# --------------------------------------------------------------------------
def _category_path(cid, by_id):
    """สร้างชื่อเต็มของหมวดหมู่เดิม เช่น 'All / Tradeable / Products'."""
    parts = []
    seen = set()
    cur = cid
    while cur and cur in by_id and cur not in seen:
        seen.add(cur)
        parts.append(by_id[cur]['name'])
        cur = by_id[cur]['parent_id']
    return ' / '.join(reversed(parts))


def _category_cache(env):
    """จับคู่หมวดหมู่สินค้าเดิม -> product.category ของ Odoo 19 (ผ่าน product_category_map.csv)."""
    mapping = common.load_map('product_category_map.csv')
    rows = legacy.fetch_all("SELECT id, name, parent_id FROM product_category")
    by_id = {r['id']: r for r in rows}
    Categ = env['product.category']

    cache = {}
    missing = []
    for cid in by_id:
        path = _category_path(cid, by_id)
        name = (mapping.get(path) or {}).get('od19_category')
        if not name:
            missing.append(path)
            continue
        categ = Categ.search([('name', '=', name)], limit=1)
        if not categ:
            categ = Categ.create({'name': name})
        cache[cid] = categ.id

    if missing:
        common.log("คำเตือน: หมวดหมู่เดิมยังไม่มี mapping %d รายการ: %s"
                   % (len(missing), ', '.join(sorted(missing))))
    return cache


def _uom_cache(env):
    """จับคู่ชื่อหน่วยนับเดิม -> uom.uom ของ Odoo 19 (ผ่าน uom_map.csv)."""
    mapping = common.load_map('uom_map.csv')
    Uom = env['uom.uom'].with_context(active_test=False)
    cache = {}
    for od15_name, row in mapping.items():
        od19_name = (row.get('od19_uom') or od15_name).strip()
        uom = Uom.search([('name', '=', od19_name)], limit=1)
        if not uom:
            common.log("คำเตือน: ไม่พบหน่วยนับ '%s' ใน Odoo 19 (จาก legacy '%s')"
                       % (od19_name, od15_name))
            continue
        cache[od15_name] = uom.id
    return cache


def _tax_cache(env):
    """จับคู่ชื่อภาษีเดิม -> account.tax ของ Odoo 19 (ผ่าน tax_map.csv)."""
    mapping = common.load_map('tax_map.csv')
    src_type = {r['name']: r['type_tax_use']
                for r in legacy.fetch_all("SELECT name, type_tax_use FROM account_tax")}
    Tax = env['account.tax'].with_context(active_test=False)

    cache = {}
    for od15_name, row in mapping.items():
        od19_name = (row.get('od19_tax_name') or '').strip()
        if not od19_name:
            continue
        od19_type = _TAX_TYPE.get(src_type.get(od15_name, ''), 'purchase')
        tax = Tax.search([('name', '=', od19_name),
                          ('type_tax_use', '=', od19_type)], limit=1)
        if not tax:
            common.log("คำเตือน: ไม่พบภาษี OD19 '%s' (ชนิด %s) สำหรับ '%s'"
                       % (od19_name, od19_type, od15_name))
            continue
        cache[od15_name] = tax.id
    return cache


# --------------------------------------------------------------------------
# 1) สินค้า (product.template)
# --------------------------------------------------------------------------
def _sync_products(env, stats, uoms, cats, taxes):
    rows = legacy.fetch_all(_PRODUCT_SQL)
    cust = _tax_rel('product_taxes_rel')
    supp = _tax_rel('product_supplier_taxes_rel')
    costs = _standard_price()
    has_storable = 'is_storable' in env['product.template']._fields

    multi_variant = []
    for row in rows:
        vals = _to_vals(row, uoms, cats, taxes, cust, supp, costs, has_storable)
        try:
            _rec, action = common.upsert('product.template', row['tmpl_id'], vals)
        except Exception as exc:
            common.log("ผิดพลาด: นำเข้าสินค้า legacy id=%s ('%s') ไม่ได้: %s"
                       % (row['tmpl_id'], row.get('name'), exc))
            stats.error += 1
            continue
        stats.bump(action)
        if (row.get('variant_count') or 1) > 1:
            multi_variant.append(row['tmpl_id'])

    common.log("สินค้า: ตรวจ %d รายการ" % len(rows))
    if multi_variant:
        common.log("คำเตือน: สินค้า %d รายการมีหลาย variant ในระบบเดิม — "
                   "นำเข้าเฉพาะระดับ template (id: %s)"
                   % (len(multi_variant), ', '.join(str(x) for x in multi_variant)))


def _tax_rel(table):
    """อ่านความสัมพันธ์ภาษีต่อ product_template -> {tmpl_id: [ชื่อภาษีเดิม]}.

    หมายเหตุ: คอลัมน์ prod_id ของตารางความสัมพันธ์อ้างถึง product_template
    """
    rel = {}
    for r in legacy.fetch_all(
            "SELECT r.prod_id, t.name FROM %s r "
            "JOIN account_tax t ON t.id = r.tax_id" % table):
        rel.setdefault(r['prod_id'], []).append(r['name'])
    return rel


def _standard_price():
    """อ่านต้นทุนสินค้า (standard_price) จาก ir_property ของระบบเดิม.

    ใน Odoo 15 ฟิลด์ที่เป็น company-dependent (เช่น standard_price) ถูกเก็บใน
    ตาราง ir_property โดย res_id อยู่ในรูปแบบ 'product.product,<id>'
    """
    rows = legacy.fetch_all(
        "SELECT split_part(ip.res_id, ',', 2)::int AS variant_id, ip.value_float "
        "FROM ir_property ip "
        "JOIN ir_model_fields f ON f.id = ip.fields_id "
        "WHERE f.model = 'product.product' AND f.name = 'standard_price' "
        "  AND ip.res_id LIKE 'product.product,%' AND ip.value_float IS NOT NULL")
    return {r['variant_id']: r['value_float'] for r in rows}


def _tax_ids(names, taxes):
    """แปลงรายชื่อภาษีเดิมเป็น id ของ account.tax ใน Odoo 19 (ข้ามที่จับคู่ไม่ได้)."""
    if not names:
        return []
    return sorted({taxes[n] for n in names if n in taxes})


def _to_vals(row, uoms, cats, taxes, cust, supp, costs, has_storable):
    """แปลงข้อมูลสินค้าจากระบบเดิมเป็นค่าฟิลด์ของ product.template ใน Odoo 19."""
    od19_type, is_storable = _PRODUCT_TYPE.get(row.get('type'), ('consu', False))
    vals = {
        'name': (row.get('name') or '').strip() or ('Product %s' % row['tmpl_id']),
        'type': od19_type,
        'sale_ok': bool(row.get('sale_ok')),
        'purchase_ok': bool(row.get('purchase_ok')),
        'list_price': row.get('list_price') or 0.0,
        'standard_price': costs.get(row.get('variant_id'), 0.0) or 0.0,
        'default_code': (row.get('default_code') or '').strip() or False,
        'barcode': (row.get('barcode') or '').strip() or False,
    }
    if has_storable:
        vals['is_storable'] = is_storable

    uom_id = uoms.get(row.get('uom_name'))
    if uom_id:
        vals['uom_id'] = uom_id

    categ_id = cats.get(row.get('categ_id'))
    if categ_id:
        vals['categ_id'] = categ_id

    ct = _tax_ids(cust.get(row['tmpl_id']), taxes)
    if ct:
        vals['taxes_id'] = [(6, 0, ct)]
    st = _tax_ids(supp.get(row['tmpl_id']), taxes)
    if st:
        vals['supplier_taxes_id'] = [(6, 0, st)]
    return vals


# --------------------------------------------------------------------------
# 2) รายการราคา (product.pricelist.item)
# --------------------------------------------------------------------------
def _sync_pricelist_items(env, stats, cats):
    rows = legacy.fetch_all(
        "SELECT id, pricelist_id, applied_on, compute_price, base, fixed_price, "
        "       percent_price, price_discount, price_surcharge, price_round, "
        "       min_quantity, categ_id, product_tmpl_id, date_start, date_end "
        "FROM product_pricelist_item ORDER BY id")
    if not rows:
        common.log("รายการราคา: ไม่มีข้อมูล")
        return

    imd = env['ir.model.data']

    def xmlid_res(model, legacy_id):
        return imd._xmlid_to_res_id(
            common.get_xmlid(model, legacy_id), raise_if_not_found=False)

    skipped = 0
    for r in rows:
        applied_on = r.get('applied_on') or '3_global'
        pl_id = xmlid_res('product.pricelist', r['pricelist_id'])
        if not pl_id:
            common.log("คำเตือน: ข้ามรายการราคา id=%s — ไม่พบนโยบายราคา legacy id=%s"
                       % (r['id'], r['pricelist_id']))
            skipped += 1
            continue

        vals = {
            'pricelist_id': pl_id,
            'applied_on': applied_on,
            'compute_price': r.get('compute_price') or 'fixed',
            'base': r.get('base') or 'list_price',
            'fixed_price': r.get('fixed_price') or 0.0,
            'percent_price': r.get('percent_price') or 0.0,
            'price_discount': r.get('price_discount') or 0.0,
            'price_surcharge': r.get('price_surcharge') or 0.0,
            'price_round': r.get('price_round') or 0.0,
            'min_quantity': r.get('min_quantity') or 0.0,
            'date_start': r.get('date_start'),
            'date_end': r.get('date_end'),
        }

        # ต้องมี "เป้าหมาย" ของกฎครบถ้วน มิฉะนั้น Odoo จะปฏิเสธการบันทึก
        # (เช่น applied_on='1_product' แต่ไม่ระบุสินค้า) — กรณีนี้ให้ข้ามรายการนั้น
        # สาเหตุที่พบบ่อย: สินค้าต้นทางถูกปิดใช้งาน จึงไม่ได้นำเข้า
        if applied_on == '0_product_variant':
            target = (xmlid_res('product.product', r['product_id'])
                      if r.get('product_id') else None)
            if not target:
                common.log("คำเตือน: ข้ามรายการราคา id=%s — ไม่พบสินค้า (variant) "
                           "legacy id=%s (อาจเป็นสินค้าที่ปิดใช้งาน)"
                           % (r['id'], r.get('product_id')))
                skipped += 1
                continue
            vals['product_id'] = target
        elif applied_on == '1_product':
            target = (xmlid_res('product.template', r['product_tmpl_id'])
                      if r.get('product_tmpl_id') else None)
            if not target:
                common.log("คำเตือน: ข้ามรายการราคา id=%s — ไม่พบสินค้า legacy id=%s "
                           "(อาจเป็นสินค้าที่ปิดใช้งาน)"
                           % (r['id'], r.get('product_tmpl_id')))
                skipped += 1
                continue
            vals['product_tmpl_id'] = target
        elif applied_on == '2_product_category':
            cid = cats.get(r['categ_id']) if r.get('categ_id') else None
            if not cid:
                common.log("คำเตือน: ข้ามรายการราคา id=%s — ไม่พบหมวดหมู่ legacy id=%s"
                           % (r['id'], r.get('categ_id')))
                skipped += 1
                continue
            vals['categ_id'] = cid
        # applied_on == '3_global' ไม่ต้องระบุเป้าหมาย

        try:
            _rec, action = common.upsert('product.pricelist.item', r['id'], vals)
        except Exception as exc:
            common.log("ผิดพลาด: นำเข้ารายการราคา legacy id=%s ไม่ได้: %s" % (r['id'], exc))
            stats.error += 1
            continue
        stats.bump(action)

    common.log("รายการราคา: ตรวจ %d รายการ (ข้าม %d)" % (len(rows), skipped))

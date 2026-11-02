# -*- coding: utf-8 -*-
"""s03_partners — นำเข้าคู่ค้า (ลูกค้า/ผู้ขาย)

ตัวอย่างอ้างอิงฉบับเต็มที่ step อื่น ๆ ใช้เป็นต้นแบบ:
    อ่านข้อมูลจากระบบเดิม (read-only) -> transform -> upsert ผ่าน ORM
    ทุก record ถูกผูก External ID __import15__.res_partner.<id> จึงรันซ้ำได้ไม่ซ้ำข้อมูล
"""
import common

# คอลัมน์ที่ต้องการอ่านจาก legacy (จะถูกกรองเหลือเฉพาะคอลัมน์ที่มีจริง)
_WANTED_COLUMNS = [
    'id', 'name', 'is_company', 'active',
    'customer_rank', 'supplier_rank', 'email', 'phone', 'mobile',
    'website', 'street', 'street2', 'city', 'zip', 'vat',
    'country_id', 'property_payment_term_id', 'property_supplier_payment_term_id',
    # ฟิลด์เฉพาะของระบบเดิม (มี/ไม่มีก็ได้ จะถูกตรวจสอบ existence ก่อนใช้)
    'tax_name', 'branch_code', 'tax_branch_code', 'name_en', 'fax',
]

# ค่า VAT ที่เป็น placeholder ของระบบเดิม (ไม่ใช่เลขภาษีจริง) — ต้องตัดทิ้ง
_VAT_PLACEHOLDERS = {'-', '--', '---', '0', '00', '000', '.', 'n/a', 'na', 'none', 'null'}


def _clean_vat(raw):
    """ทำความสะอาดค่า VAT จากระบบเดิม.

    คืนค่า False เมื่อเป็นค่าว่าง/placeholder/อักขระซ้ำทั้งหมด (เช่น '0000000000000')
    เพื่อไม่ให้ Odoo (base_vat) ปฏิเสธการบันทึก ส่วนค่าอื่นคงไว้ตามเดิม
    """
    vat = (raw or '').strip()
    if not vat:
        return False
    if vat.lower() in _VAT_PLACEHOLDERS:
        return False
    if len(set(vat)) == 1:
        return False
    return vat


def _clean_branch_code(raw, fallback=None):
    """ทำความสะอาดรหัสสาขา (branch_code) ให้เป็นเลข 5 หลักตามที่ Odoo กำหนด.

    * ตัวเลขไม่ครบ 5 หลัก -> เติม 0 ข้างหน้า (เช่น '0001' -> '00001')
    * ค่าที่ไม่ใช่ตัวเลข (เช่น '-') -> ตัดทิ้ง (False) เพื่อไม่ให้ Odoo ปฏิเสธการบันทึก
    """
    code = str(raw if raw not in (None, '') else (fallback or '')).strip()
    if not code or not code.isdigit():
        return False
    return code.zfill(5)[:5]


def run(stats):
    common.log("s03_partners: เริ่มนำเข้าคู่ค้า")
    rows = _fetch_partners()
    common.log("s03_partners: พบคู่ค้าที่ต้องนำเข้า %d ราย" % len(rows))

    env = common.odoo_env()
    partner_fields = env['res.partner']._fields
    has_thai_fields = 'tax_name' in partner_fields and 'branch_code' in partner_fields
    if not has_thai_fields:
        common.log("คำเตือน: ไม่พบฟิลด์ไทย (tax_name/branch_code) — จะไม่นำเข้าชื่อภาษี/รหัสสาขา "
                   "(ตรวจว่าติดตั้ง od19_partner_thai_fields แล้วหรือยัง)")

    country_ids = _country_cache(rows)
    terms = _payment_term_cache()

    for row in rows:
        vals = _to_vals(row, country_ids, terms, partner_fields, has_thai_fields)
        if not vals:
            stats.skipped += 1
            continue
        # ปิดการตรวจ VAT ของ Odoo ชั่วคราว: เลขภาษีจากระบบเดิมบางรายไม่ผ่าน checksum
        # (พิมพ์ผิด/ไม่ครบหลัก) — คงค่าไว้ตามจริงเพื่อให้แก้ที่ต้นทางภายหลัง
        _rec, action = common.upsert('res.partner', row['id'], vals,
                                     context={'no_vat_validation': True})
        stats.bump(action)

    common.log("s03_partners: เสร็จสิ้น")


def _legacy_columns(table):
    """อ่านรายชื่อคอลัมน์จริงของตารางในระบบเดิม."""
    import legacy
    rows = legacy.fetch_all(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,))
    return {r['column_name'] for r in rows}


def _fetch_partners():
    """อ่านคู่ค้าจากระบบเดิม (ลูกค้า/ผู้ขายที่ยังใช้งาน ไม่รวมบริษัทภายใน)."""
    import legacy
    cols = _legacy_columns('res_partner')

    core = ['id', 'name', 'is_company', 'active']
    wanted = core + [
        c for c in _WANTED_COLUMNS
        if c in cols and c not in core
    ]
    select = ', '.join('p.%s' % c for c in wanted)

    pay_term = 'p.property_payment_term_id' if 'property_payment_term_id' in cols else 'NULL'
    supp_term = 'p.property_supplier_payment_term_id' if 'property_supplier_payment_term_id' in cols else 'NULL'

    sql = (
        "SELECT %(select)s, c.code AS country_code, "
        "       pt.name AS payment_term_name, ps.name AS supplier_term_name "
        "FROM res_partner p "
        "LEFT JOIN res_country c ON c.id = p.country_id "
        "LEFT JOIN account_payment_term pt ON pt.id = %(pay_term)s "
        "LEFT JOIN account_payment_term ps ON ps.id = %(supp_term)s "
        "WHERE p.active = true "
        "  AND (COALESCE(p.customer_rank, 0) > 0 OR COALESCE(p.supplier_rank, 0) > 0 "
        "       OR p.id IN (SELECT partner_id FROM project_project WHERE partner_id IS NOT NULL) "
        # คู่ค้าที่มียอดลูกหนี้/เจ้าหนี้ค้างใน GL ต้องนำเข้าด้วย มิฉะนั้นยอดยกมา AR/AP จะขาดคู่ค้า
        "       OR p.id IN (SELECT DISTINCT partner_id FROM account_move_line "
        "                   WHERE partner_id IS NOT NULL) "
        # คู่ค้าที่ถูกอ้างถึงในทะเบียนย่อยภาษีหัก ณ ที่จ่าย (ระบบเดิมไม่ได้ตั้ง supplier_rank)
        # ต้องนำเข้าด้วย มิฉะนั้นใบรับรองหัก ณ ที่จ่ายจะขาดผู้รับเงิน
        "       OR p.id IN (SELECT partner_id FROM dtr_wht WHERE partner_id IS NOT NULL)) "
        "  AND p.id NOT IN (SELECT partner_id FROM res_company WHERE partner_id IS NOT NULL)"
        % {'select': select, 'pay_term': pay_term, 'supp_term': supp_term}
    )
    return legacy.fetch_all(sql)


def _country_cache(rows):
    """สร้าง cache รหัสประเทศ -> id ของ res.country ใน Odoo 19."""
    codes = {r.get('country_code') for r in rows if r.get('country_code')}
    if not codes:
        return {}
    env = common.odoo_env()
    countries = env['res.country'].search([('code', 'in', list(codes))])
    return {c.code: c.id for c in countries}


def _payment_term_cache():
    """สร้าง cache ชื่อเงื่อนไขชำระ (legacy) -> id ของ account.payment.term (Odoo 19)."""
    mapping = common.load_map('payment_term_map.csv')
    env = common.odoo_env()
    cache = {}
    for od15_name, row in mapping.items():
        od19_name = row.get('od19_term_name')
        if not od19_name:
            continue
        term = env['account.payment.term'].search([('name', '=', od19_name)], limit=1)
        if not term:
            common.log("คำเตือน: ไม่พบเงื่อนไขชำระ '%s' ใน Odoo 19 (จาก legacy '%s')"
                       % (od19_name, od15_name))
            continue
        cache[od15_name] = term.id
    return cache


def _to_vals(row, country_ids, terms, partner_fields, has_thai_fields):
    """แปลงข้อมูลคู่ค้าจากระบบเดิมเป็นค่าฟิลด์ของ Odoo 19."""
    name = (row.get('name') or '').strip()
    if not name:
        common.log("ข้ามคู่ค้า legacy id=%s เพราะไม่มีชื่อ" % row.get('id'))
        return None

    vals = {
        'name': name,
        'company_type': 'company' if row.get('is_company') else 'person',
        'email': row.get('email') or False,
        'phone': row.get('phone') or False,
        'mobile': row.get('mobile') or False,
        'website': row.get('website') or False,
        'street': row.get('street') or False,
        'street2': row.get('street2') or False,
        'city': row.get('city') or False,
        'zip': row.get('zip') or False,
        'vat': _clean_vat(row.get('vat')),
        'customer_rank': 1 if (row.get('customer_rank') or 0) > 0 else 0,
        'supplier_rank': 1 if (row.get('supplier_rank') or 0) > 0 else 0,
    }

    # ประเทศ (map ด้วยรหัสประเทศ)
    country_code = row.get('country_code')
    if country_code:
        country_id = country_ids.get(country_code)
        if country_id:
            vals['country_id'] = country_id
        else:
            common.log("คำเตือน: ไม่พบประเทศรหัส '%s' (partner legacy id=%s)"
                       % (country_code, row.get('id')))

    # เงื่อนไขชำระ (map ด้วยชื่อผ่าน payment_term_map.csv)
    pay_term = row.get('payment_term_name')
    if pay_term and pay_term in terms:
        vals['property_payment_term_id'] = terms[pay_term]
    supp_term = row.get('supplier_term_name')
    if supp_term and supp_term in terms:
        vals['property_supplier_payment_term_id'] = terms[supp_term]

    # ฟิลด์ไทย (เฉพาะเมื่อมีจริงใน Odoo 19)
    if has_thai_fields:
        tax_name = row.get('tax_name') or name
        if tax_name:
            vals['tax_name'] = tax_name
        branch_code = _clean_branch_code(row.get('branch_code'), row.get('tax_branch_code'))
        if branch_code:
            vals['branch_code'] = branch_code

    # ฟิลด์เสริม (ใส่เฉพาะเมื่อมีจริง)
    if 'fax' in partner_fields and row.get('fax'):
        vals['fax'] = row['fax']
    if 'name_en' in partner_fields and row.get('name_en'):
        vals['name_en'] = row['name_en']

    return vals

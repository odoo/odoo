# -*- coding: utf-8 -*-
"""s05_terms — นำเข้าเทมเพลตเงื่อนไขซื้อ/ขาย (master data)

แหล่งข้อมูลเดิม (Odoo 15): โมเดลรายงานเงื่อนไขของโมดูล `autoinfo_sale` /
`autoinfo_purchase` ซึ่งเก็บ "เงื่อนไขมาตรฐาน" ที่ผู้ใช้เลือกไว้บนใบเสนอราคา
และใบสั่งซื้อ ปลายทางคือเทมเพลตเงื่อนไขของ Odoo 19

    เงื่อนไขขาย  -> od19.sale.term.template
    เงื่อนไขซื้อ -> od19.purchase.term.template

หมายเหตุการแปลงข้อมูล:
    * ตารางเดิมมีเฉพาะ id / name / description (ไม่มีคอลัมน์ active)
    * `description` เป็น HTML — ต้องแปลงเป็นข้อความล้วน เพราะรายงานของ Odoo 19
      แสดงฟิลด์ content ด้วย t-out ซึ่ง escape HTML (ถ้าเก็บแท็กไว้จะเห็นแท็ก
      เป็นตัวอักษรบนใบเสนอราคา)
    * ชื่อเทมเพลตของ Odoo 19 ซ้ำไม่ได้ (unique(name, term_type)) — ชื่อที่ซ้ำกัน
      ในแหล่งเดียวกันจึงถูกรวมเข้าด้วยกัน

การรันซ้ำ (idempotent): ผูก External ID
__import15__.<model>.<source>_<legacy_id> โดยใช้ record แรกที่พบของแต่ละชื่อ
"""
import html
import re

import common

# (คีย์แหล่งข้อมูล, ตารางในระบบเดิม, โมเดลในระบบเดิม, term_type ปลายทาง)
_SALE_SOURCES = (
    ('sale_price', 'dtr_sale_price_report',
     'dtr.sale.price.report', 'price'),
    ('sale_delivery', 'dtr_sale_delivery_report',
     'dtr.sale.delivery.report', 'delivery'),
    ('sale_pay_product', 'dtr_sale_payment_product_report',
     'dtr.sale.payment.product.report', 'payment_product'),
    ('sale_pay_engineering', 'dtr_sale_payment_engineering_report',
     'dtr.sale.payment.engineering.report', 'payment_engineering'),
    ('sale_validity', 'dtr_sale_validity_report',
     'dtr.sale.validity.report', 'validity'),
    ('sale_warranty', 'dtr_sale_warranty_report',
     'dtr.sale.warranty.report', 'warranty'),
    ('sale_credit', 'dtr_sale_credit_report',
     'dtr.sale.credit.report', 'credit'),
)

_PURCHASE_SOURCES = (
    ('pur_warranty', 'dtr_purchase_warranty_report',
     'dtr.purchase.warranty.report', 'warranty'),
    ('pur_delivery_to', 'dtr_purchase_delivery_to_report',
     'dtr.purchase.delivery.to.report', 'delivery_to'),
    ('pur_term', 'dtr_purchase_term_report',
     'dtr.purchase.term.report', 'payment_term'),
    ('pur_shipment', 'dtr_purchase_shipment_report',
     'dtr.purchase.shipment.report', 'shipment'),
    ('pur_weight', 'dtr_purchase_weight_report',
     'dtr.purchase.weight.report', 'weight'),
)

# ชื่อที่เป็นเพียงเครื่องหมายหรือคำบอกว่า "ไม่มีเงื่อนไข" — ไม่นำเข้า
_NAME_PLACEHOLDERS = {'-', '--', '---', '.', 'n/a', 'na', 'none', 'null', 'nan'}
_ONLY_PUNCT = re.compile(r'^[\W_]+$', re.UNICODE)
_TAG = re.compile(r'<[^>]+>')
_BREAK = re.compile(r'(?i)<br\s*/?>|</p\s*>|</div\s*>|</li\s*>')

# ความยาวสูงสุดของชื่อเทมเพลต (กันข้อมูลเพี้ยนจากระบบเดิม)
_NAME_MAX = 250


def _html_to_text(raw):
    """แปลงข้อความ HTML จากระบบเดิมเป็นข้อความล้วน (คืนค่า False ถ้าว่าง)."""
    text = raw or ''
    if not text.strip():
        return False
    text = _BREAK.sub('\n', text)
    text = _TAG.sub('', text)
    text = html.unescape(text).replace('\xa0', ' ')
    lines = [ln.strip() for ln in text.splitlines()]
    return '\n'.join(ln for ln in lines if ln) or False


def _clean_name(raw):
    """ทำความสะอาดชื่อเทมเพลตจากระบบเดิม (คืนค่า False ถ้าใช้ไม่ได้)."""
    name = ' '.join((raw or '').split())
    if not name:
        return False
    if name.lower() in _NAME_PLACEHOLDERS or _ONLY_PUNCT.match(name):
        return False
    return name[:_NAME_MAX].strip()


def _fetch(table):
    """อ่านเงื่อนไขจากตารางในระบบเดิม (read-only ผ่าน legacy.py)."""
    import legacy
    return legacy.fetch_all(
        'SELECT id, name, description FROM %s ORDER BY id' % table)


def _sync(sources, model, stats):
    """นำเข้าเทมเพลตเงื่อนไขหนึ่งชุด (ขายหรือซื้อ) เข้าโมเดลปลายทาง."""
    for key, table, legacy_model, term_type in sources:
        try:
            rows = _fetch(table)
        except Exception as exc:
            common.log("ผิดพลาด: อ่านตาราง %s ไม่ได้: %s" % (table, exc))
            stats.error += 1
            continue

        # รวมชื่อที่ซ้ำกัน (unique(name, term_type) ของ Odoo 19) — เก็บ record แรก
        unique = {}
        skipped = 0
        for row in rows:
            name = _clean_name(row.get('name'))
            if not name:
                skipped += 1
                continue
            norm = name.casefold()
            if norm in unique:
                skipped += 1
                continue
            unique[norm] = (name, row)

        for name, row in unique.values():
            vals = {
                'name': name,
                'term_type': term_type,
                'content': _html_to_text(row.get('description')),
                'active': True,
            }
            _rec, action = common.upsert(
                model, '%s_%s' % (key, row['id']), vals)
            stats.bump(action)

        common.log("%s -> %s (%s): พบ %d แถว นำเข้า %d แถว "
                   "(ชื่อซ้ำ/ตัดทิ้ง %d)"
                   % (legacy_model, model, term_type,
                      len(rows), len(unique), skipped))


def run(stats):
    common.log("s05_terms: เริ่มนำเข้าเทมเพลตเงื่อนไขซื้อ/ขาย")
    _sync(_SALE_SOURCES, 'od19.sale.term.template', stats)
    _sync(_PURCHASE_SOURCES, 'od19.purchase.term.template', stats)
    common.log("s05_terms: เสร็จสิ้น")

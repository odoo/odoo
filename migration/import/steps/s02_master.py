# -*- coding: utf-8 -*-
"""s02_master — ข้อมูลหลัก: สมุดรายวัน / เงื่อนไขชำระ / หน่วยนับ / ราคา / ภาษี

หลักการ:
    * สร้างเฉพาะรายการที่ยังไม่มีใน Odoo 19 (ตรวจด้วย code/name) — รันซ้ำได้
    * ทุกรายการที่สร้างจะได้ External ID __import15__.<model>.<ค่าอ้างอิงเดิม>
      ผ่าน common.upsert จึงปลอดภัยเมื่อรันซ้ำ
    * ภาษีในขั้นตอนนี้ทำหน้าที่ "ตรวจสอบการจับคู่" เท่านั้น
      (ชุดภาษีของ Odoo 19 ถูก seed ไว้แล้ว — ไม่สร้างซ้ำ)
"""
import common
import legacy

# OD15 (option) -> OD19 (delay_type)
_TERM_DELAY = {
    'day_after_invoice_date': 'days_after',
    'day_following_month': 'days_after_end_of_month',
    'day_current_month': 'days_end_of_month_on_the',
}

# OD15 type_tax_use -> OD19 type_tax_use ('payment' ของเดิมคือ WHT -> purchase)
_TAX_TYPE = {'sale': 'sale', 'purchase': 'purchase', 'payment': 'purchase'}


def run(stats):
    env = common.odoo_env()
    _sync_journals(env, stats)
    _sync_payment_terms(env, stats)
    _sync_uoms(env, stats)
    _sync_pricelists(env, stats)
    _check_taxes(env, stats)


# --------------------------------------------------------------------------
# 1) สมุดรายวัน (account.journal)
# --------------------------------------------------------------------------
def _sync_journals(env, stats):
    mapping = common.load_map('journal_map.csv')
    Journal = env['account.journal']

    for od15_code, row in mapping.items():
        od19_code = (row.get('od19_journal_code') or od15_code).strip()
        if Journal.search([('code', '=', od19_code)], limit=1):
            stats.skipped += 1
            continue

        src = legacy.fetch_one(
            "SELECT name, type FROM account_journal WHERE code = %s", (od15_code,))
        if not src:
            common.log("คำเตือน: ไม่พบสมุดรายวัน '%s' ในระบบเดิม" % od15_code)
            stats.error += 1
            continue

        _rec, action = common.upsert('account.journal', od15_code, {
            'name': src['name'],
            'code': od19_code,
            'type': src['type'],
        })
        stats.bump(action)

    common.log("สมุดรายวัน: ตรวจ %d รายการ" % len(mapping))


# --------------------------------------------------------------------------
# 2) เงื่อนไขการชำระเงิน (account.payment.term)
# --------------------------------------------------------------------------
def _sync_payment_terms(env, stats):
    mapping = common.load_map('payment_term_map.csv')
    Term = env['account.payment.term']

    for od15_name, row in mapping.items():
        od19_name = (row.get('od19_term_name') or od15_name).strip()
        if Term.search([('name', '=', od19_name)], limit=1):
            stats.skipped += 1
            continue

        rows = legacy.fetch_all(
            "SELECT value, value_amount, days, option FROM account_payment_term_line "
            "WHERE payment_id = (SELECT id FROM account_payment_term WHERE name = %s) "
            "ORDER BY sequence, id", (od15_name,))
        if not rows:
            common.log("คำเตือน: ไม่พบเงื่อนไขชำระ '%s' ในระบบเดิม" % od15_name)
            stats.error += 1
            continue

        _rec, action = common.upsert('account.payment.term', od15_name, {
            'name': od19_name,
            'line_ids': _term_lines(rows),
        })
        stats.bump(action)

    common.log("เงื่อนไขชำระ: ตรวจ %d รายการ" % len(mapping))


def _term_lines(rows):
    """แปลง account.payment.term.line ของ OD15 -> OD19 (value: percent/fixed)."""
    percent_sum = sum((r['value_amount'] or 0.0) for r in rows if r['value'] == 'percent')
    lines = []
    for r in rows:
        if r['value'] == 'balance':
            # OD19 ไม่มีค่า 'balance' — ใช้ percent ของยอดคงเหลือที่เหลือ
            amount = max(0.0, 100.0 - percent_sum)
        else:
            amount = r['value_amount'] or 0.0
        lines.append((0, 0, {
            'value': 'percent',
            'value_amount': amount,
            'nb_days': r['days'] or 0,
            'delay_type': _TERM_DELAY.get(r['option'], 'days_after'),
        }))
    return lines


# --------------------------------------------------------------------------
# 3) หน่วยนับ (uom.uom)
# --------------------------------------------------------------------------
def _sync_uoms(env, stats):
    mapping = common.load_map('uom_map.csv')
    Uom = env['uom.uom'].with_context(active_test=False)

    for od15_name, row in mapping.items():
        od19_name = (row.get('od19_uom') or od15_name).strip()
        if Uom.search([('name', '=', od19_name)], limit=1):
            stats.skipped += 1
            continue
        # OD19 ไม่มี uom.category/ uom_type แล้ว — สร้างเป็นหน่วยอ้างอิง (reference unit)
        _rec, action = common.upsert('uom.uom', od15_name, {
            'name': od19_name,
            'rounding': 0.01,
        })
        stats.bump(action)

    common.log("หน่วยนับ: ตรวจ %d รายการ" % len(mapping))


# --------------------------------------------------------------------------
# 4) นโยบายราคา (product.pricelist) — เฉพาะตัวเปล่า
# --------------------------------------------------------------------------
def _sync_pricelists(env, stats):
    # หมายเหตุ: ห้าม browse ด้วย id ของ res.currency จากระบบเดิมโดยตรง เพราะ id
    # ไม่ตรงกันข้ามฐานข้อมูล — ต้องจับคู่ด้วย "รหัสสกุลเงิน" (name) แทน
    rows = legacy.fetch_all(
        "SELECT p.id, p.name, c.name AS currency_code "
        "FROM product_pricelist p "
        "LEFT JOIN res_currency c ON c.id = p.currency_id "
        "WHERE p.active = true ORDER BY p.id")
    Currency = env['res.currency'].with_context(active_test=False)

    for r in rows:
        code = (r.get('currency_code') or '').strip()
        currency = Currency.search([('name', '=', code)], limit=1) if code else None
        if not currency:
            common.log("คำเตือน: ไม่พบสกุลเงิน '%s' ของนโยบายราคา '%s'"
                       % (code, r['name']))
            stats.error += 1
            continue
        if not currency.active:
            # เปิดใช้งานสกุลเงินที่บริษัทเดิมใช้ เพื่อให้นโยบายราคาใช้งานได้
            currency.active = True
        _rec, action = common.upsert('product.pricelist', r['id'], {
            'name': r['name'],
            'currency_id': currency.id,
        })
        stats.bump(action)

    common.log("นโยบายราคา: ตรวจ %d รายการ (รายการราคา/items จะนำเข้าหลังสินค้า s04)"
               % len(rows))


# --------------------------------------------------------------------------
# 5) ภาษี (account.tax) — ตรวจสอบการจับคู่กับชุดภาษีที่ seed ไว้
# --------------------------------------------------------------------------
def _check_taxes(env, stats):
    mapping = common.load_map('tax_map.csv')
    Tax = env['account.tax'].with_context(active_test=False)
    matched = 0
    unresolved = []

    for od15_name, row in mapping.items():
        target = (row.get('od19_tax_name') or '').strip()
        if not target:
            unresolved.append(od15_name)
            continue

        src = legacy.fetch_one(
            "SELECT type_tax_use FROM account_tax WHERE name = %s", (od15_name,))
        od19_type = _TAX_TYPE.get(src['type_tax_use'] if src else '', 'purchase')
        if Tax.search([('name', '=', target),
                       ('type_tax_use', '=', od19_type)], limit=1):
            matched += 1
        else:
            common.log("ผิดพลาด: ไม่พบภาษี OD19 '%s' (ชนิด %s) สำหรับ '%s'"
                       % (target, od19_type, od15_name))
            stats.error += 1

    stats.skipped += matched
    common.log("ภาษี: จับคู่สำเร็จ %d รายการ | ยังไม่จับคู่ %d รายการ"
               % (matched, len(unresolved)))
    if unresolved:
        common.log("ภาษีที่ยังไม่จับคู่ (ดูรายละเอียดใน tax_map.csv):")
        for name in unresolved:
            common.log("  - %s" % name)

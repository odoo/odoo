# -*- coding: utf-8 -*-
"""dash_sales_history — นำเข้าเอกสารขายย้อนหลัง (ค่าเริ่มต้น 2023-2025) จาก Odoo 15
เข้า "ฐานข้อมูลทดสอบ" เพื่อทดสอบฟีเจอร์เปรียบเทียบช่วงเวลา YtY/MtM/QtQ ของ od19_dashboard

หลักการ
    * ฐานข้อมูลต้นทาง (od15_stage) อ่านอย่างเดียวเท่านั้น (legacy.py บังคับ read-only)
    * ฐานข้อมูลปลายทางเขียนผ่าน ORM เท่านั้น + External ID __import15__.<model>.<id>
      จึงรันซ้ำได้ (idempotent) ไม่เกิดข้อมูลซ้ำ
    * สคริปต์นี้เป็น "เครื่องมือทดสอบ" แยกจาก pipeline migration หลัก (s01-s09)
      ซึ่งตามแผนจะไม่ย้ายประวัติธุรกรรม

วิธีรัน (จาก root โปรเจกต์ c:\\odoo-dev\\odoo19):
    $env:OD15_USER="odoo"; $env:OD15_PASSWORD="odoo123"
    $env:MIG_LIMIT="50"    # ไม่ใส่ = ทั้งหมด (0 = ไม่จำกัด)
    venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_dash_test --no-http `
        --db-filter=^odoo19_dash_test$ < migration\\import\\dash_sales_history.py
"""
import os
import sys
import json
import datetime


def _bootstrap_import_dir():
    """หาโฟลเดอร์ migration/import เพื่อใส่ใน sys.path (__file__ ใช้ไม่ได้ใน odoo shell)."""
    candidate = os.environ.get('MIG_IMPORT_DIR')
    if candidate and os.path.isfile(os.path.join(candidate, 'common.py')):
        return os.path.abspath(candidate)
    here = os.getcwd()
    for _ in range(6):
        guess = os.path.join(here, 'migration', 'import')
        if os.path.isfile(os.path.join(guess, 'common.py')):
            return guess
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise RuntimeError("ไม่พบโฟลเดอร์ migration/import — กำหนด MIG_IMPORT_DIR")


_IMPORT_DIR = _bootstrap_import_dir()
if _IMPORT_DIR not in sys.path:
    sys.path.insert(0, _IMPORT_DIR)

import common  # noqa: E402
import legacy  # noqa: E402

# --------------------------------------------------------------------------
# พารามิเตอร์ (อ่านจาก environment variable)
# --------------------------------------------------------------------------
YEAR_FROM = int(os.environ.get('MIG_YEAR_FROM', '2023'))
YEAR_TO = int(os.environ.get('MIG_YEAR_TO', '2025'))
LIMIT = int(os.environ.get('MIG_LIMIT', '0') or '0')
COMMIT_EVERY = 200

DATE_FROM = datetime.date(YEAR_FROM, 1, 1)
DATE_TO = datetime.date(YEAR_TO + 1, 1, 1)

# สถานะใบสั่งขายที่ถือว่า "ยืนยันแล้ว" ในระบบเดิม
SO_STATES = ('sale', 'done')

# แคชการแมป legacy id -> id ของ Odoo 19
partner_map = {}   # legacy res_partner.id -> res.partner.id
product_map = {}   # legacy product_product.id -> (product.product.id, uom id)

# ชื่อฟิลด์หน่วยนับของ sale.order.line (ต่างกันตามเวอร์ชัน)
UOM_FIELD = 'product_uom'


def _lim(sql):
    """เติม LIMIT ต่อท้ายเมื่อมีการจำกัดจำนวน (ใช้ทดสอบ)."""
    if LIMIT > 0:
        return sql + " LIMIT %d" % LIMIT
    return sql


def _json_name(raw, _depth=0):
    """ดึงชื่อจากฟิลด์ name ของ Odoo 15 (รองรับทั้ง text ธรรมดาและ jsonb)."""
    if raw is None:
        return ''
    if isinstance(raw, dict):
        for key in ('th_TH', 'en_US', 'en'):
            if raw.get(key):
                return str(raw[key])
        for value in raw.values():
            if value:
                return _json_name(value, _depth + 1)
        return ''
    text = str(raw).strip()
    # ระบบเดิมบางฐานเก็บ name เป็น text ธรรมดา — แปลง JSON เฉพาะเมื่อขึ้นต้นด้วย '{'
    if not text or _depth >= 3 or not text.startswith('{'):
        return text
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return text
    if isinstance(parsed, dict):
        return _json_name(parsed, _depth + 1)
    return text


def _maybe_commit(env, stats):
    """commit เป็นช่วง ๆ เพื่อลดภาระ transaction ยาว (อนุญาตเฉพาะเครื่องมือทดสอบนี้)."""
    done = stats.created + stats.updated + stats.skipped + stats.error
    if done and done % COMMIT_EVERY == 0:
        env.cr.commit()
        common.log("... progress %s" % stats.summary())


# --------------------------------------------------------------------------
# ขั้นที่ 1 — ลูกค้าที่ถูกอ้างอิงในเอกสารช่วงปีเป้าหมาย
# --------------------------------------------------------------------------
def phase_partners(env):
    common.set_step('dash.partners')
    sql = (
        "SELECT p.id, p.name, p.is_company, p.vat, p.street, p.city, p.zip, p.phone, p.email "
        "FROM res_partner p WHERE p.id IN ("
        "  SELECT partner_id FROM sale_order WHERE partner_id IS NOT NULL "
        "    AND date_order >= %s AND date_order < %s"
        "  UNION "
        "  SELECT partner_id FROM account_move WHERE partner_id IS NOT NULL "
        "    AND move_type = 'out_invoice' AND state = 'posted' "
        "    AND invoice_date >= %s AND invoice_date < %s)"
        " ORDER BY p.id")
    rows = legacy.fetch_all(sql, (DATE_FROM, DATE_TO, DATE_FROM, DATE_TO))
    common.log("dash.partners: พบลูกค้าที่อ้างอิง %d ราย" % len(rows))

    stats = common.Stats('partners')
    for r in rows:
        name = (r.get('name') or '').strip() or ('Partner %s' % r['id'])
        vals = {
            'name': name,
            'company_type': 'company' if r.get('is_company') else 'person',
            'vat': r.get('vat') or False,
            'street': r.get('street') or False,
            'city': r.get('city') or False,
            'zip': r.get('zip') or False,
            'phone': r.get('phone') or False,
            'email': r.get('email') or False,
            'customer_rank': 1,
        }
        rec, action = common.upsert('res.partner', r['id'], vals)
        stats.bump(action)
        if rec:
            partner_map[r['id']] = rec.id
    common.log("dash.partners: %s" % stats.summary())


# --------------------------------------------------------------------------
# ขั้นที่ 2 — สินค้าที่ถูกอ้างอิง (นำเข้าเป็น service เพื่อไม่ให้กระทบสต็อก)
# --------------------------------------------------------------------------
def phase_products(env):
    common.set_step('dash.products')
    sql = (
        "SELECT pp.id, pt.name AS name_json, pp.default_code "
        "FROM product_product pp JOIN product_template pt ON pt.id = pp.product_tmpl_id "
        "WHERE pp.id IN ("
        "  SELECT sol.product_id FROM sale_order_line sol "
        "    JOIN sale_order so ON so.id = sol.order_id "
        "    WHERE sol.product_id IS NOT NULL "
        "      AND so.date_order >= %s AND so.date_order < %s"
        "  UNION "
        "  SELECT aml.product_id FROM account_move_line aml "
        "    JOIN account_move am ON am.id = aml.move_id "
        "    WHERE aml.product_id IS NOT NULL AND am.move_type = 'out_invoice' "
        "      AND am.state = 'posted' AND am.invoice_date >= %s AND am.invoice_date < %s)"
        " ORDER BY pp.id")
    rows = legacy.fetch_all(sql, (DATE_FROM, DATE_TO, DATE_FROM, DATE_TO))
    common.log("dash.products: พบสินค้าที่อ้างอิง %d รายการ" % len(rows))

    stats = common.Stats('products')
    for r in rows:
        name = _json_name(r.get('name_json')) or ('Product %s' % r['id'])
        vals = {
            'name': name,
            'type': 'service',
            'default_code': r.get('default_code') or False,
            'sale_ok': True,
            'purchase_ok': False,
        }
        rec, action = common.upsert('product.template', r['id'], vals)
        stats.bump(action)
        if rec and rec.product_variant_id:
            variant = rec.product_variant_id
            product_map[r['id']] = (variant.id, variant.uom_id.id)
    common.log("dash.products: %s" % stats.summary())


# --------------------------------------------------------------------------
# ขั้นที่ 3 — ใบสั่งขาย (sale.order) ในสถานะยืนยันแล้ว
# --------------------------------------------------------------------------
def phase_sale_orders(env):
    common.set_step('dash.sale_orders')
    orders = legacy.fetch_all(_lim(
        "SELECT id, date_order, partner_id, client_order_ref "
        "FROM sale_order WHERE state = ANY(%s) "
        "AND date_order >= %s AND date_order < %s ORDER BY id"),
        (list(SO_STATES), DATE_FROM, DATE_TO))
    common.log("dash.sale_orders: พบใบสั่งขาย %d ใบ" % len(orders))
    if not orders:
        return

    ids = [o['id'] for o in orders]
    lines = legacy.fetch_all(
        "SELECT id, order_id, name, product_id, product_uom_qty, price_unit, discount, "
        "       display_type, sequence "
        "FROM sale_order_line WHERE order_id = ANY(%s) ORDER BY order_id, sequence, id",
        (ids,))
    lines_by_order = {}
    for ln in lines:
        lines_by_order.setdefault(ln['order_id'], []).append(ln)

    stats = common.Stats('sale_orders')
    for o in orders:
        pid = partner_map.get(o.get('partner_id'))
        if not pid:
            stats.skipped += 1
            continue

        order_lines = []
        for ln in lines_by_order.get(o['id'], []):
            if ln.get('display_type'):
                continue
            pm = product_map.get(ln.get('product_id'))
            if not pm:
                continue
            lv = {
                'product_id': pm[0],
                'name': ln.get('name') or '',
                'product_uom_qty': float(ln.get('product_uom_qty') or 0.0),
                'price_unit': float(ln.get('price_unit') or 0.0),
                'discount': float(ln.get('discount') or 0.0),
            }
            if UOM_FIELD:
                lv[UOM_FIELD] = pm[1]
            order_lines.append((0, 0, lv))

        if not order_lines:
            stats.skipped += 1
            continue

        vals = {
            'partner_id': pid,
            'date_order': o.get('date_order'),
            'client_order_ref': o.get('client_order_ref') or False,
            'order_line': order_lines,
        }
        rec, action = common.upsert('sale.order', o['id'], vals)
        stats.bump(action)
        if rec and rec.state != 'sale':
            rec.write({'state': 'sale'})
        _maybe_commit(env, stats)
    common.log("dash.sale_orders: %s" % stats.summary())


# --------------------------------------------------------------------------
# ขั้นที่ 4 — ใบแจ้งหนี้ลูกค้า (account.move: out_invoice, posted)
# --------------------------------------------------------------------------
def phase_invoices(env):
    common.set_step('dash.invoices')
    sale_journal = env['account.journal'].search(
        [('type', '=', 'sale'), ('company_id', '=', env.company.id)], limit=1)
    if not sale_journal:
        common.log("คำเตือน: ไม่พบสมุดรายวันขาย — ข้ามการนำเข้าใบแจ้งหนี้")
        return

    invoices = legacy.fetch_all(_lim(
        "SELECT id, invoice_date, date, invoice_date_due, partner_id, ref, amount_total "
        "FROM account_move WHERE move_type = 'out_invoice' AND state = 'posted' "
        "AND invoice_date >= %s AND invoice_date < %s ORDER BY id"),
        (DATE_FROM, DATE_TO))
    common.log("dash.invoices: พบใบแจ้งหนี้ %d ใบ" % len(invoices))
    if not invoices:
        return

    # หมายเหตุ: ไม่สร้างบรรทัดจาก account_move_line ของระบบเดิมโดยตรง เพราะคอลัมน์
    # discount ในฐานนี้เก็บเป็น "จำนวนเงิน" ไม่ใช่เปอร์เซ็นต์ ทำให้ยอดเพี้ยน/ติดลบ
    # และ Odoo 19 ปฏิเสธการ post ใบแจ้งหนี้ที่มียอดติดลบ
    # dashboard ต้องการเฉพาะยอดรวม (amount_total / amount_residual) จึงสร้าง
    # บรรทัดสรุปบรรทัดเดียวจาก amount_total พร้อมล้างภาษีเพื่อให้ยอดตรงกับระบบเดิม
    stats = common.Stats('invoices')
    for inv in invoices:
        pid = partner_map.get(inv.get('partner_id'))
        if not pid:
            stats.skipped += 1
            continue

        inv_date = inv.get('invoice_date')
        vals = {
            'move_type': 'out_invoice',
            'partner_id': pid,
            'invoice_date': inv_date,
            'date': inv.get('date') or inv_date,
            'invoice_date_due': inv.get('invoice_date_due') or inv_date,
            'journal_id': sale_journal.id,
            'ref': inv.get('ref') or False,
            'invoice_line_ids': [(0, 0, {
                'name': 'ยอดยกมาจากระบบเดิม',
                'quantity': 1.0,
                'price_unit': float(inv.get('amount_total') or 0.0),
                'tax_ids': [(6, 0, [])],
            })],
        }
        rec, action = common.upsert('account.move', inv['id'], vals)
        stats.bump(action)
        if rec and rec.state == 'draft':
            rec.action_post()
        _maybe_commit(env, stats)
    common.log("dash.invoices: %s" % stats.summary())


# --------------------------------------------------------------------------
# ตรวจผล — เทียบยอดรวมรายปีระหว่างระบบเดิมกับ Odoo 19
# --------------------------------------------------------------------------
def verify(env):
    common.set_step('dash.verify')
    for yr in range(YEAR_FROM, YEAR_TO + 1):
        d1 = datetime.date(yr, 1, 1)
        d2 = datetime.date(yr + 1, 1, 1)

        so = env['sale.order'].search([
            ('date_order', '>=', d1), ('date_order', '<', d2), ('state', '=', 'sale')])
        inv = env['account.move'].search([
            ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
            ('invoice_date', '>=', d1), ('invoice_date', '<', d2)])

        legacy_so = legacy.fetch_one(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount_total), 0) AS s FROM sale_order "
            "WHERE state IN ('sale', 'done') AND date_order >= %s AND date_order < %s", (d1, d2))
        legacy_inv = legacy.fetch_one(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount_total), 0) AS s FROM account_move "
            "WHERE move_type = 'out_invoice' AND state = 'posted' "
            "AND invoice_date >= %s AND invoice_date < %s", (d1, d2))

        common.log(
            "ปี %d | SO  od15=%s/%.2f  od19=%d/%.2f | INV  od15=%s/%.2f  od19=%d/%.2f" % (
                yr,
                legacy_so['c'], float(legacy_so['s']),
                len(so), sum(so.mapped('amount_total')),
                legacy_inv['c'], float(legacy_inv['s']),
                len(inv), sum(inv.mapped('amount_total')),
            ))


def main():
    common.init(env)  # noqa: F821 — env มีให้โดย odoo shell
    global UOM_FIELD
    SOL_FIELDS = env['sale.order.line']._fields  # noqa: F821
    UOM_FIELD = ('product_uom_id' if 'product_uom_id' in SOL_FIELDS
                 else ('product_uom' if 'product_uom' in SOL_FIELDS else ''))

    common.log("dash_sales_history: เริ่ม | ปี %d-%d | LIMIT=%s | DRY_RUN=%s" % (
        YEAR_FROM, YEAR_TO, LIMIT or 'ทั้งหมด', common.DRY_RUN))

    phase_partners(env)      # noqa: F821
    phase_products(env)      # noqa: F821
    phase_sale_orders(env)   # noqa: F821
    phase_invoices(env)      # noqa: F821
    verify(env)              # noqa: F821

    env.cr.commit()          # noqa: F821
    common.log("dash_sales_history: เสร็จสิ้น")


main()

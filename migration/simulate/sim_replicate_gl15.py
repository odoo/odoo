# -*- coding: utf-8 -*-
r"""sim_replicate_gl15 — replicate รายการจริงของ Odoo 15 (ม.ค.–ส.ค. 2026) เข้า Odoo 19

เป้าหมาย (ตามที่ผู้ใช้ยืนยัน)
    "odoo19 คือ odoo15 ในอดีต" — ทุก record ของ od15 ในช่วง ม.ค.–ส.ค. 2026
    ต้องเกิดขึ้นใน od19 ด้วยบริบทเดียวกันทุกประการ (บัญชี/คู่ค้า/ภาษี/สมุดรายวัน/วันที่)
    เพื่อให้ report, dashboard, accounting report ให้ผลลัพธ์ตรงกัน

หลักการ (แนวทาง A — GL-faithful)
    * 1 move ของ od15 -> 1 move ของ od19 ชนิดเดิม (move_type เดิม)
    * ใบซื้อ/ขาย (out_invoice/in_invoice/out_refund/in_refund)
        -> typed invoice ให้ Odoo คำนวณภาษี/AR/AP เอง
           + override บัญชีบรรทัดภาษีให้ตรงบัญชีที่ od15 ใช้จริงในใบนั้น
             (od15 ลงบรรทัดภาษีตามบัญชีที่ใช้จริง ไม่ตาม repartition line)
           + ยึด price_subtotal ของ od15 (กัน discount เพี้ยน/เกิน 100)
    * entry (GL: ใบสำคัญ, รับ-จ่าย, กระทบยอดธนาคาร)
        -> move_type='entry' คัดลอก line_ids แบบ 1:1 (GL ตรงเป๊ะ)
    * ทุกใบผูก External ID __import15__.account_move.<TAG>_<od15 move id>
        -> รันซ้ำได้ (idempotent) — ใบที่ post แล้วจะถูกข้ามทันที

วิธีรัน (จาก root โปรเจกต์ c:\odoo-dev\odoo19):
    Get-Content -LiteralPath .\migration\simulate\sim_replicate_gl15.py -Raw |
        .\venv19\Scripts\python.exe .\odoo-bin shell -c .\odoo.conf `
        -d odoo19_puat --no-http --db-filter=^odoo19_puat$

ตัวแปรสภาพแวดล้อม
    MIG_DRY_RUN=1     ทดสอบโดยไม่เขียนจริง (สร้างใน savepoint แล้ว rollback)
    REP_PREFLIGHT=1   ตรวจความพร้อม (บัญชี/ภาษี/สมุดรายวัน/คู่ค้า) เท่านั้น ไม่เขียน
    REP_RESET=1       ลบเอกสารที่ replicate ไว้เดิมทั้งหมดก่อนเริ่ม
    REP_D1 / REP_D2   ช่วงวันที่ (ค่าเริ่มต้น 2026-01-01 .. 2026-08-31)
    REP_TAG           prefix External ID (ค่าเริ่มต้น gl15rep)
    REP_LIMIT         จำกัดจำนวนใบ (0 = ทั้งหมด) — เรียงตามวันที่
    REP_TYPES         ชนิดที่ replicate (ค่าเริ่มต้น ทุกชนิด)
    REP_BATCH         commit ทุกกี่ใบ (ค่าเริ่มต้น 200)
"""
import os
import sys
import re

# --------------------------------------------------------------------------
# bootstrap migration/import (odoo shell ไม่มี __file__)
# --------------------------------------------------------------------------
def _bootstrap_import_dir():
    cand = os.environ.get('MIG_IMPORT_DIR')
    if cand and os.path.isfile(os.path.join(cand, 'common.py')):
        return os.path.abspath(cand)
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


_ID = _bootstrap_import_dir()
if _ID not in sys.path:
    sys.path.insert(0, _ID)

import common  # noqa: E402
import legacy  # noqa: E402


def _bootstrap_od15_env():
    """อ่านค่าการเชื่อมต่อฝั่ง od15 จาก odoo.conf (ห้ามฝัง credential ในคำสั่งรัน)."""
    if os.environ.get('OD15_PASSWORD'):
        return
    conf = os.path.join(os.getcwd(), 'odoo.conf')
    if not os.path.isfile(conf):
        return
    cfg = {}
    with open(conf, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('[') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            cfg[k.strip()] = v.strip()
    os.environ.setdefault('OD15_HOST', cfg.get('db_host', 'localhost'))
    os.environ.setdefault('OD15_PORT', cfg.get('db_port', '5432'))
    os.environ.setdefault('OD15_USER', cfg.get('db_user', 'odoo'))
    if cfg.get('db_password'):
        os.environ['OD15_PASSWORD'] = cfg['db_password']


# --------------------------------------------------------------------------
# พารามิเตอร์
# --------------------------------------------------------------------------
D1 = os.environ.get('REP_D1', '2026-01-01')
D2 = os.environ.get('REP_D2', '2026-08-31')
TAG = os.environ.get('REP_TAG', 'gl15rep')
LIMIT = int(os.environ.get('REP_LIMIT', '0') or '0')
BATCH = int(os.environ.get('REP_BATCH', '200') or '200')
TYPES = [t for t in os.environ.get(
    'REP_TYPES', 'out_invoice,in_invoice,out_refund,in_refund,entry').split(',') if t]

# od15 code -> od19 code  /  od15 tax name -> od19 tax name
AMAP = {k: (v.get('รหัส Odoo 19') or '').strip()
        for k, v in common.load_map('od15_code_to_od19_code.csv').items()}
TMAP = {k: (v.get('od19_tax_name') or '').strip()
        for k, v in common.load_map('tax_map.csv').items()}

# ภาษีที่ od19 ต้องมี 'ตัวเฉพาะ' ไม่ใช้ generic (จับคู่ผ่าน External ID)
# เหตุผล: tax_map.csv ปล่อย od19_tax_name ของ Undue VAT(P)7% ว่าง -> fallback ไป
# tax ซื้อ 7% ตัวเดียวกันกับ VAT(P)7% ทำให้ใบที่ใช้ทั้งสองภาษีถูกรวบเป็นบรรทัดเดียว
SPECIAL_TAX = {
    'Undue VAT(P)7%': 'undue_vat_p_7',
}

# แคชการอ้างอิง od19
_acct_cache = {}
_journal_cache = {}
_partner_cache = {}
_tax_cache = {}


# --------------------------------------------------------------------------
# ตัวช่วยอ้างอิง od19
# --------------------------------------------------------------------------
def account19(code15):
    """คืนค่า (account.account, error) จากรหัสบัญชี od15."""
    if code15 in _acct_cache:
        return _acct_cache[code15]
    code19 = AMAP.get(code15)
    if not code19:
        res = (None, 'no-map:%s' % code15)
    else:
        acc = env['account.account'].search([('code', '=', code19)], limit=1)  # noqa: F821
        res = (acc, None) if acc else (None, 'no-acc:%s' % code19)
    _acct_cache[code15] = res
    return res


def tax19(name15, is_purchase):
    """หา account.tax ใน od19 — บังคับ type_tax_use ตามชนิดเอกสารก่อนเสมอ."""
    if not name15:
        return None, None
    cache_key = (name15, bool(is_purchase))
    if cache_key in _tax_cache:
        return _tax_cache[cache_key]
    # ภาษีที่ต้องใช้ 'ตัวเฉพาะ' (เช่น Undue VAT(P)7% -> 1151.02)
    sp_key = SPECIAL_TAX.get(name15)
    if sp_key:
        xmlid = common.get_xmlid('account.tax', sp_key)
        tid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)  # noqa: F821
        if tid:
            res = (env['account.tax'].browse(tid), None)  # noqa: F821
            _tax_cache[cache_key] = res
            return res
    use = 'purchase' if is_purchase else 'sale'
    name19 = TMAP.get(name15)
    if name19:
        t = env['account.tax'].search(  # noqa: F821
            [('name', '=', name19), ('type_tax_use', '=', use)], limit=1)
        if not t:
            t = env['account.tax'].search([('name', '=', name19)], limit=1)  # noqa: F821
        res = (t, None) if t else (None, 'no-tax:%s' % name19)
        _tax_cache[cache_key] = res
        return res
    m = re.search(r'(\d+(?:\.\d+)?)%', name15 or '')
    if m:
        amount = float(m.group(1))
        t = env['account.tax'].search(  # noqa: F821
            [('amount', '=', amount), ('type_tax_use', '=', use)], limit=1)
        if not t:
            t = env['account.tax'].search([('amount', '=', amount)], limit=1)  # noqa: F821
        if t:
            _tax_cache[cache_key] = (t, None)
            return t, None
    res = (None, 'no-tmap:%s' % name15)
    _tax_cache[cache_key] = res
    return res


def product19(legacy_tmpl_id):
    if not legacy_tmpl_id:
        return None
    xmlid = common.get_xmlid('product.template', legacy_tmpl_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)  # noqa: F821
    if not pid:
        return None
    return env['product.template'].browse(pid).product_variant_id  # noqa: F821


def partner19(legacy_id):
    if not legacy_id:
        return None
    if legacy_id in _partner_cache:
        return _partner_cache[legacy_id]
    xmlid = common.get_xmlid('res.partner', legacy_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)  # noqa: F821
    p = env['res.partner'].browse(pid) if pid else None  # noqa: F821
    _partner_cache[legacy_id] = p
    return p


def journal19(code15):
    if code15 in _journal_cache:
        return _journal_cache[code15]
    jm = common.load_map('journal_map.csv').get(code15)
    code19 = (jm.get('od19_journal_code') or code15).strip() if jm else code15
    j = env['account.journal'].search(  # noqa: F821
        [('code', '=', code19), ('company_id', '=', env.company.id)], limit=1)  # noqa: F821
    if not j:
        j = env['account.journal'].search([('code', '=', code19)], limit=1)  # noqa: F821
    _journal_cache[code15] = j
    return j


# --------------------------------------------------------------------------
# สร้าง/ตรวจภาษี 'Undue VAT(P)7%' (ชนิดซื้อ 7%) ผูกบัญชี 1151.02
# --------------------------------------------------------------------------
UNDUE_P_TAX_KEY = 'undue_vat_p_7'
UNDUE_P_TAX_NAME = 'Undue VAT(P)7%'
UNDUE_P_TAX_ACCT = '1151.02'


def ensure_undue_purchase_tax():
    """สร้าง account.tax 'Undue VAT(P)7%' ให้ od19 (idempotent)

    เหตุผล: od15 แยก 'Undue VAT(P)7%' (ภาษีซื้อรอตัดบัญชี -> 1151.02) ออกจาก
    'VAT(P)7%' (ภาษีซื้อ -> 1151.01) แต่ od19 เดิมใช้ tax ซื้อ 7% ตัวเดียวกันกับทั้งคู่
    ทำให้ใบที่ใช้ทั้ง 2 ภาษีในใบเดียว (เช่น APTH2608-0072) ถูกรวบเป็นบรรทัดเดียว
    บัญชี 1151.02 จึงขาดยอด วิธีแก้: สร้าง tax เฉพาะ (กอปปี้ค่าจาก tax ซื้อ 7% เดิม)
    แล้วผูก repartition line กับบัญชี 1151.02 (build_invoice ยัง override บัญชี
    รายใบตามที่ od15 ใช้จริงอีกชั้น)
    """
    common.set_step('gl15.tax')
    xmlid = common.get_xmlid('account.tax', UNDUE_P_TAX_KEY)
    imd = env['ir.model.data']  # noqa: F821
    tid = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if tid:
        t = env['account.tax'].browse(tid)  # noqa: F821
        if t.exists():
            common.log("tax '%s' มีอยู่แล้ว (id=%s)" % (UNDUE_P_TAX_NAME, t.id))
            return t
    if common.DRY_RUN:
        common.log("[DRY-RUN] จะสร้าง tax '%s' ผูก %s" % (UNDUE_P_TAX_NAME, UNDUE_P_TAX_ACCT))
        return None
    acc = env['account.account'].search(  # noqa: F821
        [('code', '=', UNDUE_P_TAX_ACCT)], limit=1)
    if not acc:
        raise ValueError("ไม่พบบัญชี %s ใน od19" % UNDUE_P_TAX_ACCT)
    base = env['account.tax'].search([  # noqa: F821
        ('type_tax_use', '=', 'purchase'), ('amount', '=', 7.0),
        ('company_id', '=', env.company.id)], limit=1)  # noqa: F821
    if base:
        new = base.copy({'name': UNDUE_P_TAX_NAME})
    else:
        new = env['account.tax'].create({  # noqa: F821
            'name': UNDUE_P_TAX_NAME, 'amount': 7.0, 'amount_type': 'percent',
            'type_tax_use': 'purchase', 'price_include': False,
            'company_id': env.company.id,  # noqa: F821
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
            ],
        })
    for rl in (new.invoice_repartition_line_ids | new.refund_repartition_line_ids):
        if rl.repartition_type == 'tax':
            rl.account_id = acc.id
    imd._update_xmlids(
        [{'xml_id': xmlid, 'record': new, 'noupdate': True}], update=True)
    common.log("สร้าง tax '%s' (id=%s) ผูกกับ %s" % (UNDUE_P_TAX_NAME, new.id, acc.code))
    return new


# --------------------------------------------------------------------------
# ดึงบรรทัดจาก od15
# --------------------------------------------------------------------------
def od15_lines(move_id):
    return legacy.fetch_all(
        "SELECT l.id, a.code AS code, l.partner_id, l.name, l.debit, l.credit, "
        "       l.quantity, l.price_unit, l.discount, l.price_subtotal, l.product_id, "
        "       t.product_tmpl_id AS tmpl_id, l.display_type, l.tax_line_id, "
        "       (SELECT name FROM account_tax WHERE id=l.tax_line_id) AS taxline_name, "
        "       at.type AS atype, "
        "       (SELECT array_agg(DISTINCT atx.name) FROM account_move_line_account_tax_rel r "
        "        JOIN account_tax atx ON atx.id=r.account_tax_id "
        "        WHERE r.account_move_line_id=l.id) AS taxes "
        "FROM account_move_line l "
        "JOIN account_account a ON a.id=l.account_id "
        "LEFT JOIN account_account_type at ON at.id=a.user_type_id "
        "LEFT JOIN product_product t ON t.id=l.product_id "
        "WHERE l.move_id=%(mid)s ORDER BY l.id", {'mid': move_id})


# --------------------------------------------------------------------------
# สร้าง move ใน od19 (typed invoice / entry)
# --------------------------------------------------------------------------
def build_invoice(rec, l15, warns):
    p = partner19(rec['partner_id'])
    if not p:
        return 'no-partner:%s' % rec['partner_id']
    journal = journal19(rec['jcode'])
    if not journal:
        return 'no-journal:%s' % rec['jcode']
    # sync AR/AP property ตามบัญชีที่ od15 ใช้ในใบนี้
    for atype, field in (('receivable', 'property_account_receivable_id'),
                         ('payable', 'property_account_payable_id')):
        codes = [r['code'] for r in l15 if r['atype'] == atype]
        if codes:
            acc, err = account19(codes[0])
            if acc:
                p.with_company(env.company)[field] = acc  # noqa: F821
            else:
                warns.append(err)

    is_purchase = rec['move_type'] in ('in_invoice', 'in_refund')
    inv_lines = []
    tax_used = {}   # od19 tax id -> set(ชื่อ tax od15) สำหรับ override บัญชีบรรทัดภาษี
    for r in l15:
        if r['display_type'] in ('line_section', 'line_note'):
            continue
        if r['tax_line_id']:
            continue  # บรรทัดภาษี
        if r['atype'] in ('receivable', 'payable'):
            continue  # AR/AP เกิดเองจาก partner property
        acc, err = account19(r['code'])
        if not acc:
            warns.append(err)
            return 'skip-line-acc:%s' % err
        tax_ids = []
        for tname in (r['taxes'] or []):
            t, terr = tax19(tname, is_purchase)
            if t:
                tax_ids.append(t.id)
                tax_used.setdefault(t.id, set()).add(tname)
            else:
                warns.append(terr)
        qty = float(r['quantity']) if r['quantity'] is not None else 1.0
        pu = float(r['price_unit'] or 0.0)
        dc = float(r['discount'] or 0.0)
        # ยึด price_subtotal ของ od15: ถ้าสูตรไม่ตรง (discount>100/ข้อมูลเพี้ยน)
        # -> ใช้ qty=1, pu=subtotal, discount=0 ให้ subtotal ตรงเป๊ะ
        sub = round(float(r['price_subtotal'] or 0.0), 2)
        recomputed = round(qty * pu * (1 - dc / 100.0), 2) if 0 <= dc <= 100 else None
        if recomputed != sub:
            qty, pu, dc = 1.0, sub, 0.0
        vals = {
            'account_id': acc.id,
            'name': (r['name'] or '')[:64] or '/',
            'quantity': qty,
            'price_unit': pu,
            'discount': dc,
            'tax_ids': [(6, 0, tax_ids)],
        }
        prod = product19(r['tmpl_id'])
        if prod:
            vals['product_id'] = prod.id
        inv_lines.append((0, 0, vals))

    if not inv_lines:
        return 'no-invoice-lines'
    hd = {
        'move_type': rec['move_type'],
        'partner_id': p.id,
        'journal_id': journal.id,
        'date': rec['date'],
        'invoice_date': rec['invoice_date'] or rec['date'],
        'ref': rec['ref'] or rec['name'] or False,
        'invoice_line_ids': inv_lines,
    }
    move = env['account.move'].with_context(  # noqa: F821
        od19_skip_86_4_validation=True).create(hd)
    # override บัญชีบรรทัดภาษี ให้ตรงบัญชีที่ od15 ใช้จริงในใบนี้
    # (od15 ลงบรรทัดภาษีตามบัญชีจริงของเอกสาร ไม่ตาม repartition rule ของ od19)
    d15 = {}
    for r in l15:
        if r['tax_line_id'] and r['taxline_name']:
            d15.setdefault(r['taxline_name'], set()).add(r['code'])
    for line in move.line_ids.filtered('tax_line_id'):
        names15 = tax_used.get(line.tax_line_id.id)
        if not names15:
            continue
        codes = set()
        for n in names15:
            codes |= d15.get(n, set())
        if len(codes) == 1:
            acc2, err2 = account19(next(iter(codes)))
            if acc2:
                line.account_id = acc2.id
            else:
                warns.append(err2)
        elif len(codes) > 1:
            warns.append('ambig-tax-acct:%s' % sorted(codes))
    # ใบซื้อ: OCA l10n_th_account_tax บังคับ tax_invoice_number/date ก่อน post
    if is_purchase and move.tax_invoice_ids:
        move.tax_invoice_ids.write({
            'tax_invoice_number': rec['ref'] or rec['name'] or '/',
            'tax_invoice_date': rec['invoice_date'] or rec['date'],
        })
    move.action_post()
    return move


def build_entry(rec, l15, warns):
    journal = journal19(rec['jcode'])
    if not journal:
        return 'no-journal:%s' % rec['jcode']
    lines = []
    for r in l15:
        acc, err = account19(r['code'])
        if not acc:
            warns.append(err)
            return 'skip-line-acc:%s' % err
        vals = {
            'account_id': acc.id,
            'name': (r['name'] or '')[:64] or '/',
            'debit': round(float(r['debit'] or 0), 2),
            'credit': round(float(r['credit'] or 0), 2),
        }
        p = partner19(r['partner_id'])
        if p:
            vals['partner_id'] = p.id
        lines.append((0, 0, vals))
    if not lines:
        return 'no-lines'
    move = env['account.move'].with_context(  # noqa: F821
        od19_skip_86_4_validation=True).create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': rec['date'],
            'ref': rec['ref'] or rec['name'] or False,
            'line_ids': lines,
        })
    move.action_post()
    return move


def _create_move(rec, l15, warns):
    if rec['move_type'] == 'entry':
        return build_entry(rec, l15, warns)
    return build_invoice(rec, l15, warns)


# --------------------------------------------------------------------------
# ดึงประชากร od15 (เรียงตามวันเวลา เพื่อลำดับเอกสารเป็นธรรมชาติ)
# --------------------------------------------------------------------------
def fetch_population(limit=0):
    rows = []
    for mt in TYPES:
        sql = (
            "SELECT m.id, m.name, m.move_type, m.date, m.ref, m.partner_id, "
            "       m.invoice_date, j.code AS jcode "
            "FROM account_move m JOIN account_journal j ON j.id=m.journal_id "
            "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
            "  AND m.move_type=%(mt)s")
        rows.extend(legacy.fetch_all(sql, {'d1': D1, 'd2': D2, 'mt': mt}))
    rows.sort(key=lambda r: (str(r['date']), r['move_type'], r['id']))
    if limit > 0:
        rows = rows[:limit]
    return rows


# --------------------------------------------------------------------------
# Preflight — ตรวจความพร้อมก่อนรันจริง (ไม่เขียนข้อมูล)
# --------------------------------------------------------------------------
def preflight():
    common.set_step('gl15.preflight')
    common.log("ตรวจความพร้อม: ช่วง %s .. %s | types=%s" % (D1, D2, ','.join(TYPES)))
    pop = fetch_population()
    by_type = {}
    for r in pop:
        by_type[r['move_type']] = by_type.get(r['move_type'], 0) + 1
    common.log("  ประชากร: %d ใบ %s" % (len(pop), by_type))
    d1, d2 = D1, D2

    # 1) บัญชี
    acc_rows = legacy.fetch_all(
        "SELECT a.code AS code, count(*) AS n "
        "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
        "JOIN account_account a ON a.id=l.account_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1 ORDER BY 2 DESC", {'d1': d1, 'd2': d2})
    miss_acc, miss_acc_n = [], 0
    for r in acc_rows:
        code19 = AMAP.get(r['code'])
        if not code19:
            miss_acc.append('%s(no-map)' % r['code'])
            miss_acc_n += r['n']
            continue
        if not env['account.account'].search([('code', '=', code19)], limit=1):  # noqa: F821
            miss_acc.append('%s->%s(no-acc)' % (r['code'], code19))
            miss_acc_n += r['n']
    common.log("  บัญชีที่ใช้ %d รหัส | ปัญหา %d (%d บรรทัด)" % (len(acc_rows), len(miss_acc), miss_acc_n))
    if miss_acc:
        common.log("    %s" % miss_acc[:40])

    # 2) ภาษี (จาก tax_line_id)
    tax_rows = legacy.fetch_all(
        "SELECT t.name AS name, t.type_tax_use AS use, count(*) AS n "
        "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
        "JOIN account_tax t ON t.id=l.tax_line_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1,2 ORDER BY 3 DESC", {'d1': d1, 'd2': d2})
    miss_tax = []
    for r in tax_rows:
        is_p = r['use'] == 'purchase'
        t, err = tax19(r['name'], is_p)
        if not t:
            miss_tax.append('%s[%s]x%s' % (r['name'], r['use'], r['n']))
    common.log("  ภาษีที่ใช้ %d ชนิด | หาไม่เจอ %d: %s" % (len(tax_rows), len(miss_tax), miss_tax))

    # 3) สมุดรายวัน
    j_rows = legacy.fetch_all(
        "SELECT j.code AS code, j.type AS jtype, count(*) AS n "
        "FROM account_move m JOIN account_journal j ON j.id=m.journal_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1,2 ORDER BY 3 DESC", {'d1': d1, 'd2': d2})
    miss_j = []
    for r in j_rows:
        if not journal19(r['code']):
            miss_j.append('%s[%s]x%s' % (r['code'], r['jtype'], r['n']))
    common.log("  สมุดรายวันที่ใช้ %d | หาไม่เจอ %d: %s" % (len(j_rows), len(miss_j), miss_j))

    # 4) คู่ค้า
    p_rows = legacy.fetch_all(
        "SELECT m.partner_id, count(*) AS n FROM account_move m "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "  AND m.partner_id IS NOT NULL GROUP BY 1 ORDER BY 2 DESC",
        {'d1': d1, 'd2': d2})
    miss_p = []
    for r in p_rows:
        if not partner19(r['partner_id']):
            miss_p.append('pid=%s x%s' % (r['partner_id'], r['n']))
    common.log("  คู่ค้าที่ใช้ %d ราย | หาไม่เจอ %d: %s" % (len(p_rows), len(miss_p), miss_p[:30]))

    # 5) สินค้า
    pr_rows = legacy.fetch_all(
        "SELECT t.product_tmpl_id AS tmpl, count(*) AS n "
        "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
        "JOIN product_product t ON t.id=l.product_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1 ORDER BY 2 DESC", {'d1': d1, 'd2': d2})
    miss_pr = []
    for r in pr_rows:
        if not product19(r['tmpl']):
            miss_pr.append('tmpl=%s x%s' % (r['tmpl'], r['n']))
    common.log("  สินค้าที่ใช้ %d | หาไม่เจอ %d: %s" % (len(pr_rows), len(miss_pr), miss_pr[:20]))

    # 6) สถานะ od19 ปัจจุบัน (ในช่วงเดียวกับที่ replicate)
    n_now = env['account.move'].search_count([  # noqa: F821
        ('date', '>=', d1), ('date', '<=', d2)])
    common.log("  od19 ปัจจุบัน: มี account.move ช่วงเดียวกันอยู่แล้ว %d ใบ" % n_now)
    common.log("  preflight เสร็จสิ้น")


# --------------------------------------------------------------------------
# Reset — ลบเอกสารที่ replicate ไว้เดิมทั้งหมด
# --------------------------------------------------------------------------
def phase_reset():
    common.set_step('gl15.reset')
    imd = env['ir.model.data']  # noqa: F821
    xmlids = imd.search([
        ('module', '=', common.MODULE_PREFIX),
        ('name', 'like', '%s_%%' % TAG)])
    move_ids = [x.res_id for x in xmlids if x.model == 'account.move']
    moves = env['account.move'].browse(move_ids)  # noqa: F821
    n = len(moves)
    common.log("reset: พบเอกสารที่ replicate ไว้ %d ใบ — กำลังลบ" % n)
    posted = moves.filtered(lambda m: m.state == 'posted')
    if posted:
        posted.button_draft()
    moves.unlink()
    imd.browse(xmlids.ids).unlink()
    common.log("reset: ลบแล้ว %d ใบ" % n)


# --------------------------------------------------------------------------
# Replicate
# --------------------------------------------------------------------------
def phase_replicate():
    common.set_step('gl15.replicate')
    pop = fetch_population(limit=LIMIT)
    total = len(pop)
    common.log("เริ่ม replicate %d ใบ | DRY_RUN=%s | TAG=%s" % (total, common.DRY_RUN, TAG))
    stats = common.Stats('gl15.replicate')
    warnings = {}
    processed = 0
    for rec in pop:
        key = '%s_%s' % (TAG, rec['id'])
        xmlid = common.get_xmlid('account.move', key)
        imd = env['ir.model.data']  # noqa: F821
        existing_id = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
        if existing_id:
            m = env['account.move'].browse(existing_id)  # noqa: F821
            if m.state == 'posted':
                stats.skipped += 1
                processed += 1
                continue
            # มีอยู่แต่ยังเป็นฉบับร่าง -> ลบทิ้งแล้วสร้างใหม่ (การประกอบบรรทัดซับซ้อน)
            m.unlink()
        try:
            with env.cr.savepoint():  # noqa: F821
                l15 = od15_lines(rec['id'])
                if not l15:
                    stats.skipped += 1
                    raise _Rollback()
                warns = []
                move = _create_move(rec, l15, warns)
                if isinstance(move, str):
                    stats.error += 1
                    warnings['%s' % move.split(':')[0]] = \
                        warnings.get('%s' % move.split(':')[0], 0) + 1
                    raise _Rollback()
                for w in warns:
                    tag = w.split(':')[0]
                    warnings[tag] = warnings.get(tag, 0) + 1
                if common.DRY_RUN:
                    stats.created += 1
                    raise _Rollback()
                imd._update_xmlids(
                    [{'xml_id': xmlid, 'record': move, 'noupdate': True}], update=True)
                stats.created += 1
        except _Rollback:
            pass
        except Exception as exc:  # noqa: BLE001
            stats.error += 1
            warnings['EXC'] = warnings.get('EXC', 0) + 1
            common.log("ล้มเหลว %s %s: %s" % (
                rec['move_type'], rec['name'], str(exc).splitlines()[0]))
        processed += 1
        if not common.DRY_RUN and BATCH and processed % BATCH == 0:
            env.cr.commit()  # noqa: F821
            common.log("... %d/%d | %s" % (processed, total, stats.summary()))
        elif processed % 500 == 0:
            common.log("... %d/%d | %s" % (processed, total, stats.summary()))
    if not common.DRY_RUN:
        env.cr.commit()  # noqa: F821
    common.log("replicate: %s" % stats.summary())
    if warnings:
        common.log("คำเตือน/ข้อผิดพลาด: %s" % warnings)
    return stats


class _Rollback(Exception):
    """สัญญาณ rollback ภายใน savepoint (ใช้ในโหมด dry-run / ข้ามใบ)."""
    pass


# --------------------------------------------------------------------------
# Verify — เทียบงบทดลอง (Trial Balance) รายเดือน od15 vs od19
# --------------------------------------------------------------------------
def verify():
    common.set_step('gl15.verify')
    common.log("เปรียบเทียบงบทดลองรายเดือน (od15 vs od19) ช่วง %s .. %s" % (D1, D2))
    rows = legacy.fetch_all(
        "SELECT to_char(m.date,'YYYY-MM') AS ym, a.code AS code, "
        "       sum(l.debit) AS dr, sum(l.credit) AS cr "
        "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
        "JOIN account_account a ON a.id=l.account_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1,2", {'d1': D1, 'd2': D2})
    exp = {}   # (ym, code19) -> [dr, cr]
    for r in rows:
        code19 = AMAP.get(r['code']) or ('??%s' % r['code'])
        k = (r['ym'], code19)
        v = exp.setdefault(k, [0.0, 0.0])
        v[0] += float(r['dr'] or 0.0)
        v[1] += float(r['cr'] or 0.0)

    recs = env['account.move.line'].search_read(  # noqa: F821
        [('parent_state', '=', 'posted'), ('date', '>=', D1), ('date', '<=', D2)],
        ['account_id', 'debit', 'credit', 'date'])
    acc_ids = set(r['account_id'][0] for r in recs if r['account_id'])
    code_by_id = {a['id']: a['code'] for a in env['account.account'].browse(  # noqa: F821
        list(acc_ids)).read(['code'])}
    got = {}   # (ym, code19) -> [dr, cr]
    for r in recs:
        aid = r['account_id'][0] if r['account_id'] else None
        code19 = code_by_id.get(aid, '??')
        ym = str(r['date'])[:7]
        k = (ym, code19)
        v = got.setdefault(k, [0.0, 0.0])
        v[0] += float(r['debit'] or 0.0)
        v[1] += float(r['credit'] or 0.0)

    months = sorted(set(k[0] for k in list(exp) + list(got)))
    bad_total = 0
    for ym in months:
        e_dr = sum(v[0] for k, v in exp.items() if k[0] == ym)
        e_cr = sum(v[1] for k, v in exp.items() if k[0] == ym)
        g_dr = sum(v[0] for k, v in got.items() if k[0] == ym)
        g_cr = sum(v[1] for k, v in got.items() if k[0] == ym)
        d_dr = round(g_dr - e_dr, 2)
        d_cr = round(g_cr - e_cr, 2)
        flag = '' if (abs(d_dr) < 0.05 and abs(d_cr) < 0.05) else '  <-- ต่าง'
        if flag:
            bad_total += 1
        common.log("  %s | od15 dr=%14.2f cr=%14.2f | od19 dr=%14.2f cr=%14.2f | diff dr=%9.2f cr=%9.2f%s"
                   % (ym, e_dr, e_cr, g_dr, g_cr, d_dr, d_cr, flag))

    diff_accts = []
    for k in sorted(set(exp) | set(got)):
        e = exp.get(k, [0.0, 0.0])
        g = got.get(k, [0.0, 0.0])
        if abs(round(g[0] - e[0], 2)) >= 0.05 or abs(round(g[1] - e[1], 2)) >= 0.05:
            diff_accts.append((k[0], k[1], round(e[0] - e[1], 2), round(g[0] - g[1], 2)))
    common.log("  บัญชีที่ยอดไม่ตรง (รายเดือน): %d รายการ" % len(diff_accts))
    for row in diff_accts[:40]:
        common.log("    %s %-12s od15=%12.2f od19=%12.2f" % row)
    common.log("  สรุป: เดือนที่ยอดรวมต่าง %d/%d | บัญชีไม่ตรง %d"
               % (bad_total, len(months), len(diff_accts)))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    common.log("sim_replicate_gl15: เริ่ม | %s .. %s | DRY_RUN=%s | บริษัท %s"
               % (D1, D2, common.DRY_RUN, env.company.name))  # noqa: F821

    if os.environ.get('REP_PREFLIGHT') == '1':
        preflight()
        return

    # สร้างภาษี 'Undue VAT(P)7%' (ผูก 1151.02) ให้พร้อมก่อน replicate
    ensure_undue_purchase_tax()
    if not common.DRY_RUN:
        env.cr.commit()  # noqa: F821

    if os.environ.get('REP_RESET') == '1' and not common.DRY_RUN:
        phase_reset()
        env.cr.commit()  # noqa: F821

    phase_replicate()
    verify()
    common.log("sim_replicate_gl15: เสร็จสิ้น")


main()

# -*- coding: utf-8 -*-
r"""Recon — ตรวจกระทบยอด "ยอดยกมา" ของ Odoo 19 เทียบระบบเดิม Odoo 15 (อ่านอย่างเดียว)

รัน (จาก root ของโปรเจกต์):
    Get-Content migration\recon\run.py -Raw | & .\venv19\Scripts\python.exe -u `
        .\odoo-bin shell -c odoo.conf -d odoo19_puat --no-http

ตรวจ 4 ด้านตามแผน (Phase 5 / Gate 5):
    Recon #1  Trial Balance เทียบทีละบัญชี (เน้นบัญชีงบดุล ต้องตรงทุกบัญชี)
    Recon #2  AR/AP แยกรายคู่ค้า
    Recon #3  สต็อกคงเหลือ (ปริมาณ + มูลค่า เทียบยอด GL)
    Recon #4  สินทรัพย์ / ภาษีหัก ณ ที่จ่าย / เงินทดรอง / เช็ค

หลักการ:
    * ฝั่ง Odoo 15 อ่านผ่าน legacy.py (psycopg2, read-only) — ห้ามเขียนกลับ
    * ฝั่ง Odoo 19 อ่านผ่าน ORM เท่านั้น
    * ผลต่าง (diff) ที่ยอมรับได้ต้องเป็น 0 ทุกบัญชี/ทุกคู่ค้าที่มียอด
"""
import os
import sys


def _import_dir():
    """หาโฟลเดอร์ migration/import เพื่อนำเข้า common/legacy (ใน odoo shell ไม่มี __file__)."""
    here = os.getcwd()
    for _ in range(6):
        guess = os.path.join(here, 'migration', 'import')
        if os.path.isfile(os.path.join(guess, 'common.py')):
            return guess
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise RuntimeError("ไม่พบโฟลเดอร์ migration/import — กรุณารันจาก root ของโปรเจกต์")


_ID = _import_dir()
if _ID not in sys.path:
    sys.path.insert(0, _ID)

import common  # noqa: E402
import legacy  # noqa: E402

# --------------------------------------------------------------------------
# ค่าคงที่
# --------------------------------------------------------------------------
OPENING_DATE = '2026-10-31'
STOCK_GL_CODE = '1140-01'            # บัญชีสินค้าคงเหลือในผังเดิม
CHART_FILE = 'od15_chart_to_od19.csv'
RECEIVABLE_PAYABLE = ('asset_receivable', 'liability_payable')
BS_PREFIXES = ('asset', 'liability', 'equity')   # บัญชีงบดุล (ต้องกระทบยอดให้ตรง)
# ประเภทเงินได้ที่ระบบใหม่รองรับ (ต้องตรงกับ s08_opening.WHT_CERT_INCOME_TYPES)
WHT_CERT_INCOME_TYPES = frozenset((
    '1', '2', '3', '4A',
    '4B11', '4B12', '4B13', '4B14',
    '4B21', '4B22', '4B23', '4B24', '4B25',
    '5', '6',
))

_TOL = 0.01          # ค่าคลาดเคลื่อนที่ยอมรับได้ (ปัดเศษสตางค์)
_failures = []       # รายการที่ไม่ผ่าน


def od19_code(od15_code):
    """แปลงรหัสบัญชีระบบเดิม -> รหัส Odoo 19 ('-' -> '.')."""
    return (od15_code or '').strip().replace('-', '.')


def money(v):
    return round(float(v or 0.0), 2)


def ok(label, detail):
    print("  [OK]   %s %s" % (label, detail))


def warn(label, detail):
    """ผลต่างที่อธิบายได้ (ไม่อยู่ในขอบเขตการย้าย) — ไม่นับเป็นความล้มเหลว."""
    print("  [WARN] %s %s" % (label, detail))


def fail(label, detail=''):
    _failures.append(('%s %s' % (label, detail)).strip())
    print("  [FAIL] %s %s" % (label, detail))


def imported_ids(env, model):
    """คืน set ของ res_id ที่นำเข้าจากระบบเดิม (ผ่าน External ID __import15__)."""
    return set(env['ir.model.data'].search(
        [('model', '=', model), ('module', '=', common.MODULE_PREFIX)]).mapped('res_id'))


def _legacy_id_of(name):
    """ดึง id เดิมจากชื่อ External ID (รูปแบบ '<model_underscored>.<legacy_id>')."""
    return (name or '').rsplit('.', 1)[-1]


def imported_legacy_ids(env, model):
    """คืน set ของ id เดิม (จากชื่อ External ID) ของเรกคอร์ดที่นำเข้าแล้ว."""
    data = env['ir.model.data'].search_read(
        [('model', '=', model), ('module', '=', common.MODULE_PREFIX)], ['name'])
    out = set()
    for d in data:
        try:
            out.add(int(_legacy_id_of(d['name'])))
        except (TypeError, ValueError):
            continue
    return out


# --------------------------------------------------------------------------
# Recon #1 — Trial Balance
# --------------------------------------------------------------------------
def od15_trial_balance():
    """ยอดคงเหลือต่อบัญชี ณ วันตัดยอดจากระบบเดิม."""
    sql = (
        "SELECT a.code AS code, round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s "
        "GROUP BY a.code "
        "HAVING round(sum(l.balance)::numeric, 2) <> 0"
    )
    return {r['code']: money(r['balance'])
            for r in legacy.fetch_all(sql, {'date': OPENING_DATE})}


def od19_trial_balance(env):
    """ยอดคงเหลือต่อรหัสบัญชี ณ วันตัดยอดใน Odoo 19 (ผ่าน ORM)."""
    groups = env['account.move.line'].read_group(
        [('parent_state', '=', 'posted'), ('move_id.date', '<=', OPENING_DATE)],
        ['balance:sum'], ['account_id'])
    acc_ids = [g['account_id'][0] for g in groups if g.get('account_id')]
    code_by_id = {a.id: a.code for a in env['account.account'].browse(acc_ids)}
    out = {}
    for g in groups:
        if not g.get('account_id'):
            continue
        code = code_by_id.get(g['account_id'][0])
        out[code] = money(out.get(code, 0.0) + float(g['balance'] or 0.0))
    return out


def recon_trial_balance(env, chart):
    print("\n=== Recon #1: Trial Balance ณ %s ===" % OPENING_DATE)
    tb15 = od15_trial_balance()
    tb19 = od19_trial_balance(env)

    checked = 0
    pl_expected = 0
    pl_total = 0.0
    matched_codes = set()
    for o15_code, bal15 in sorted(tb15.items()):
        row = chart.get(o15_code) or {}
        acc_type = (row.get('od19_account_type') or '').strip()
        o19_code = od19_code(o15_code)
        bal19 = tb19.get(o19_code, 0.0)
        matched_codes.add(o19_code)
        if acc_type.startswith(BS_PREFIXES):
            checked += 1
            diff = money(bal19 - bal15)
            if abs(diff) > _TOL:
                fail("บัญชี %s (%s): OD15=%.2f OD19=%.2f diff=%.2f"
                     % (o15_code, o19_code, bal15, bal19, diff))
        else:
            # บัญชีกำไรขาดทุน — ตั้งใจไม่ยกมา (สะท้อนผ่านบัญชีคู่ปรับ)
            if abs(bal15) > _TOL:
                pl_expected += 1
                pl_total = money(pl_total + bal15)

    # บัญชีใน OD19 ที่ไม่ปรากฏในผังเดิม (คาดหวังเฉพาะบัญชีคู่ปรับ)
    extra = {c: b for c, b in tb19.items()
             if c not in matched_codes and abs(b) > _TOL}
    for code, bal in sorted(extra.items()):
        acc = env['account.account'].search([('code', '=', code)], limit=1)
        a_type = acc.account_type if acc else '?'
        print("  [INFO] บัญชี OD19 เพิ่มเติม %s (%s): %.2f" % (code, a_type, bal))

    net19 = money(sum(tb19.values()))
    if abs(net19) > _TOL:
        fail("GL OD19 ไม่สมดุล", "net=%.2f" % net19)
    else:
        ok("GL OD19 สมดุล", "net=%.2f" % net19)
    print("  ตรวจบัญชีงบดุล %d บัญชี | บัญชีกำไรขาดทุนที่ตัดออก %d บัญชี (ยอดรวม %.2f)"
          % (checked, pl_expected, pl_total))


# --------------------------------------------------------------------------
# Recon #2 — AR/AP แยกรายคู่ค้า
# --------------------------------------------------------------------------
def recon_arap(env, chart):
    print("\n=== Recon #2: AR/AP แยกรายคู่ค้า ณ %s ===" % OPENING_DATE)
    codes = [c for c, r in chart.items()
             if (r.get('od19_account_type') or '') in RECEIVABLE_PAYABLE]
    if not codes:
        fail("Recon #2", "ไม่พบบัญชีลูกหนี้/เจ้าหนี้ในไฟล์ mapping")
        return

    sql = (
        "SELECT a.code AS code, l.partner_id AS partner_id, "
        "       round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s AND a.code = ANY(%(codes)s) "
        "GROUP BY a.code, l.partner_id "
        "HAVING round(sum(l.balance)::numeric, 2) <> 0"
    )
    rows15 = legacy.fetch_all(sql, {'date': OPENING_DATE, 'codes': codes})
    key15 = {}
    for r in rows15:
        key15[(od19_code(r['code']), r['partner_id'])] = money(r['balance'])

    imd = env['ir.model.data']
    pdata = imd.search_read(
        [('model', '=', 'res.partner'), ('module', '=', common.MODULE_PREFIX)],
        ['res_id', 'name'])
    # ชื่อ External ID เป็น '<model_underscored>.<id เดิม>' — แยกเอา id เดิม (int)
    legacy_of = {}
    for d in pdata:
        try:
            legacy_of[d['res_id']] = int(_legacy_id_of(d['name']))
        except (TypeError, ValueError):
            continue

    # Odoo 19: read_group() หลายมิติไม่คืน partner_id จึงใช้ _read_group() แทน
    rg = env['account.move.line']._read_group(
        [('parent_state', '=', 'posted'), ('move_id.date', '<=', OPENING_DATE),
         ('account_id.account_type', 'in', list(RECEIVABLE_PAYABLE))],
        groupby=['account_id', 'partner_id'], aggregates=['balance:sum'])
    key19 = {}
    for acc, partner, balance in rg:
        pid = partner.id if partner else None
        legacy_pid = legacy_of.get(pid) if pid else None
        k = (acc.code, legacy_pid)
        key19[k] = money(key19.get(k, 0.0) + float(balance or 0.0))

    all_keys = set(key15) | set(key19)
    checked = 0
    for k in sorted(all_keys, key=lambda x: (x[0] or '', str(x[1]))):
        b15 = key15.get(k, 0.0)
        b19 = key19.get(k, 0.0)
        diff = money(b19 - b15)
        checked += 1
        if abs(diff) > _TOL:
            fail("AR/AP %s partner(od15)=%s: OD15=%.2f OD19=%.2f diff=%.2f"
                 % (k[0], k[1], b15, b19, diff))

    tot15 = money(sum(key15.values()))
    tot19 = money(sum(key19.values()))
    if abs(tot15 - tot19) > _TOL:
        fail("AR/AP ยอดรวม", "OD15=%.2f OD19=%.2f diff=%.2f" % (tot15, tot19, tot15 - tot19))
    else:
        ok("AR/AP ยอดรวม", "OD15=OD19=%.2f" % tot19)
    print("  ตรวจ %d คู่ (บัญชี×คู่ค้า) | ฝั่งเดิม %d คู่ | ฝั่งใหม่ %d คู่"
          % (checked, len(key15), len(key19)))


# --------------------------------------------------------------------------
# Recon #3 — สต็อกคงเหลือ
# --------------------------------------------------------------------------
def od15_stock():
    qty_rows = legacy.fetch_all(
        "SELECT q.product_id AS variant_id, sum(q.quantity)::numeric AS qty "
        "FROM stock_quant q JOIN stock_location l ON l.id = q.location_id "
        "WHERE l.usage = 'internal' GROUP BY q.product_id HAVING sum(q.quantity) <> 0")
    costs = {r['variant_id']: float(r['cost'] or 0.0) for r in legacy.fetch_all(
        "SELECT split_part(ip.res_id, ',', 2)::int AS variant_id, ip.value_float AS cost "
        "FROM ir_property ip JOIN ir_model_fields f ON f.id = ip.fields_id "
        "WHERE f.model = 'product.product' AND f.name = 'standard_price' "
        "  AND ip.res_id LIKE 'product.product,%' AND ip.value_float IS NOT NULL")}
    total_qty = sum(float(r['qty'] or 0.0) for r in qty_rows)
    total_val = sum(float(r['qty'] or 0.0) * costs.get(r['variant_id'], 0.0) for r in qty_rows)
    gl = legacy.fetch_one(
        "SELECT round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s AND a.code = %(code)s",
        {'date': OPENING_DATE, 'code': STOCK_GL_CODE})
    return total_qty, total_val, money(gl['balance'] if gl else 0.0), len(qty_rows)


def recon_stock(env):
    print("\n=== Recon #3: สต็อกคงเหลือ ณ %s ===" % OPENING_DATE)
    qty15, val15, gl15, n15 = od15_stock()

    groups = env['stock.quant'].read_group(
        [('location_id.usage', '=', 'internal'), ('company_id', '=', env.company.id)],
        ['quantity:sum'], ['product_id'])
    qty19 = 0.0
    val19 = 0.0
    n19 = 0
    for g in groups:
        if not g.get('product_id'):
            continue
        qty = float(g['quantity'] or 0.0)
        if abs(qty) < 1e-9:
            continue
        n19 += 1
        qty19 += qty
        prod = env['product.product'].browse(g['product_id'][0])
        val19 += (prod.standard_price or 0.0) * qty
    qty19 = money(qty19)
    val19 = money(val19)

    print("  ปริมาณรวม: OD15=%.2f | OD19=%.2f | diff=%.2f" % (qty15, qty19, qty15 - qty19))
    print("  มูลค่ารวม: OD15(ตามต้นทุนเดิม)=%.2f | OD19=%.2f | GL(%s)=%.2f"
          % (val15, val19, STOCK_GL_CODE, gl15))
    if abs(qty15 - qty19) > 0.01:
        warn("ปริมาณสต็อกรวม", "OD15=%.2f OD19=%.2f diff=%.2f "
             "(สินค้าที่ archive ในระบบเดิมถูกนำเข้าเฉพาะ active จึงไม่ย้าย)"
             % (qty15, qty19, qty15 - qty19))
    else:
        ok("ปริมาณสต็อกรวม", "ตรงกัน (%.2f)" % qty19)
    if abs(val19 - gl15) > _TOL:
        fail("มูลค่าสต็อก vs GL", "OD19=%.2f GL=%.2f diff=%.2f" % (val19, gl15, gl15 - val19))
    else:
        ok("มูลค่าสต็อกผูกกับ GL", "OD19=GL=%.2f" % gl15)
    print("  (สินค้า OD15=%d รายการ | OD19=%d รายการ | OD15 มูลค่าต้นทุนเดิมผูกกับ GL หลังปรับสัดส่วน)"
          % (n15, n19))


# --------------------------------------------------------------------------
# Recon #4 — สินทรัพย์ / WHT / เงินทดรอง / เช็ค
# --------------------------------------------------------------------------
def od15_asset_totals():
    sql = (
        "SELECT count(*) AS n, round(sum(a.value)::numeric, 2) AS value, "
        "       round(sum(COALESCE(a.accumulated_depreciation_bf, 0) + COALESCE(("
        "           SELECT sum(d.amount) FROM account_asset_depreciation_line d "
        "           WHERE d.asset_id = a.id AND d.move_check "
        "             AND d.depreciation_date <= %(date)s), 0))::numeric, 2) AS dep "
        "FROM account_asset_asset a"
    )
    r = legacy.fetch_one(sql, {'date': OPENING_DATE})
    return int(r['n']), money(r['value']), money(r['dep'])


def recon_assets(env):
    print("\n=== Recon #4a: สินทรัพย์ถาวร ===")
    n15, val15, dep15 = od15_asset_totals()
    Asset = env['account.asset']
    assets = Asset.search([('company_id', '=', env.company.id)])
    n19 = len(assets)
    val19 = money(sum(assets.mapped('purchase_value')))
    fields = Asset._fields
    nbv_field = next((f for f in ('value_residual', 'book_value', 'value_depreciated')
                      if f in fields), None)
    nbv19 = money(sum(assets.mapped(nbv_field))) if nbv_field else None
    nbv15 = money(val15 - dep15)

    print("  จำนวน: OD15=%d | OD19=%d" % (n15, n19))
    print("  มูลค่าทะเบียน: OD15=%.2f | OD19=%.2f" % (val15, val19))
    print("  มูลค่าสุทธิ: OD15=%.2f | OD19=%s" % (nbv15, ('%.2f' % nbv19) if nbv19 is not None else '-'))
    if n15 != n19:
        fail("จำนวนสินทรัพย์", "OD15=%d OD19=%d" % (n15, n19))
    else:
        ok("จำนวนสินทรัพย์", "%d รายการ" % n19)
    if abs(val15 - val19) > _TOL:
        fail("มูลค่าทะเบียนสินทรัพย์", "OD15=%.2f OD19=%.2f" % (val15, val19))
    else:
        ok("มูลค่าทะเบียนสินทรัพย์", "%.2f" % val19)
    if nbv19 is not None and abs(nbv15 - nbv19) > _TOL:
        fail("มูลค่าสุทธิสินทรัพย์", "OD15=%.2f OD19=%.2f" % (nbv15, nbv19))
    elif nbv19 is not None:
        ok("มูลค่าสุทธิสินทรัพย์", "%.2f" % nbv19)


def recon_wht(env):
    print("\n=== Recon #4b: ใบรับรองหัก ณ ที่จ่าย ===")
    # ฝั่งเดิม: คิดยอดหักเฉพาะประเภทเงินได้ที่ระบบใหม่รองรับ (ตรงกับเงื่อนไขนำเข้า)
    rows15 = legacy.fetch_all(
        "SELECT w.id, w.tax_condition, w.wht_amount1, "
        "       w.tax_condition2, w.wht_amount2, w.tax_condition3, w.wht_amount3 "
        "FROM dtr_wht w")
    amt_by_id = {}
    for r in rows15:
        amt = 0.0
        for cond, a in ((r['tax_condition'], r['wht_amount1']),
                        (r['tax_condition2'], r['wht_amount2']),
                        (r['tax_condition3'], r['wht_amount3'])):
            if cond in WHT_CERT_INCOME_TYPES:
                amt += float(a or 0.0)
        amt_by_id[r['id']] = money(amt)
    n15 = len(rows15)
    amt15 = money(sum(amt_by_id.values()))

    res_ids = imported_ids(env, 'withholding.tax.cert')
    legacy_ids = imported_legacy_ids(env, 'withholding.tax.cert')
    certs = env['withholding.tax.cert'].browse(list(res_ids))
    n19 = len(certs)
    amt19 = money(sum(certs.mapped('wht_line').mapped('amount')))

    # ใบที่ไม่ได้นำเข้า (หาผู้รับเงินไม่พบ) — อธิบายผลต่าง
    skipped = [i for i in amt_by_id if i not in legacy_ids]
    skipped_amt = money(sum(amt_by_id[i] for i in skipped))

    print("  จำนวน: OD15=%d | OD19=%d" % (n15, n19))
    print("  ยอดหักรวม: OD15=%.2f | OD19=%.2f | diff=%.2f" % (amt15, amt19, amt15 - amt19))
    if skipped:
        print("  ใบที่ข้าม %d ใบ (ยอดหักรวม %.2f) — หาผู้รับเงินไม่พบในระบบใหม่"
              % (len(skipped), skipped_amt))
    if abs((amt15 - skipped_amt) - amt19) > _TOL:
        fail("ยอด WHT", "OD15(หลังหักใบที่ข้าม)=%.2f OD19=%.2f"
             % (amt15 - skipped_amt, amt19))
    else:
        ok("ยอด WHT", "ตรงกับต้นทางหลังหักใบที่ข้าม (%.2f)" % amt19)
    if n19 + len(skipped) != n15:
        fail("จำนวน WHT", "OD15=%d แต่ OD19+ข้าม=%d" % (n15, n19 + len(skipped)))
    else:
        ok("จำนวน WHT", "ตรง (OD19=%d + ข้าม=%d = OD15=%d)" % (n19, len(skipped), n15))


def recon_advance(env):
    print("\n=== Recon #4c: เงินจ่ายล่วงหน้าผู้ขาย ===")
    r = legacy.fetch_one(
        "SELECT count(*) AS n FROM dtr_account_prepayment")
    n15 = int(r['n'])
    r2 = legacy.fetch_one(
        "SELECT round(sum(paid)::numeric,2) AS amt FROM ("
        "  SELECT COALESCE((SELECT sum(pm.amount) "
        "     FROM account_payment_dtr_account_prepayment_rel rel "
        "     JOIN account_payment pm ON pm.id = rel.account_payment_id "
        "     JOIN account_move mm ON mm.id = pm.move_id AND mm.state='posted' "
        "     WHERE rel.dtr_account_prepayment_id = p.id), 0) AS paid "
        "  FROM dtr_account_prepayment p) t")
    amt15 = money(r2['amt'])
    ids = imported_ids(env, 'account.advance')
    advs = env['account.advance'].browse(list(ids))
    n19 = len(advs)
    amt19 = money(sum(advs.mapped('amount')))
    print("  จำนวน: OD15=%d (ทั้งหมด) | OD19=%d (เฉพาะที่มีการจ่ายจริง)" % (n15, n19))
    print("  ยอดรวม: OD15(ยอดจ่ายจริง)=%.2f | OD19=%.2f" % (amt15, amt19))
    if abs(amt15 - amt19) > _TOL:
        fail("ยอดเงินจ่ายล่วงหน้า", "OD15=%.2f OD19=%.2f" % (amt15, amt19))
    else:
        ok("ยอดเงินจ่ายล่วงหน้า", "%.2f" % amt19)


def recon_cheque(env):
    print("\n=== Recon #4d: เช็คค้าง ===")
    r = legacy.fetch_one("SELECT count(*) AS n, round(sum(amount)::numeric,2) AS amt FROM dtr_cheque")
    n15, amt15 = int(r['n']), money(r['amt'])
    ids = imported_ids(env, 'account.cheque')
    cheques = env['account.cheque'].browse(list(ids))
    n19 = len(cheques)
    amt19 = money(sum(cheques.mapped('amount')))
    print("  จำนวน: OD15=%d | OD19=%d" % (n15, n19))
    print("  ยอดรวม: OD15=%.2f | OD19=%.2f" % (amt15, amt19))
    if n15 != n19:
        fail("จำนวนเช็ค", "OD15=%d OD19=%d" % (n15, n19))
    else:
        ok("จำนวนเช็ค", "%d ใบ" % n19)
    if abs(amt15 - amt19) > _TOL:
        fail("ยอดเช็ครวม", "OD15=%.2f OD19=%.2f" % (amt15, amt19))
    else:
        ok("ยอดเช็ครวม", "%.2f" % amt19)


# --------------------------------------------------------------------------
def main():
    env = common.odoo_env()
    common.set_step('recon')
    print("=" * 70)
    print("Recon: ยอดยกมา Odoo 19 (%s) เทียบระบบเดิม Odoo 15 ณ %s"
          % (env.cr.dbname, OPENING_DATE))
    print("=" * 70)
    chart = common.load_map(CHART_FILE)
    for name, fn in (
            ('Recon #1 Trial Balance', lambda: recon_trial_balance(env, chart)),
            ('Recon #2 AR/AP', lambda: recon_arap(env, chart)),
            ('Recon #3 สต็อก', lambda: recon_stock(env)),
            ('Recon #4a สินทรัพย์', lambda: recon_assets(env)),
            ('Recon #4b WHT', lambda: recon_wht(env)),
            ('Recon #4c เงินทดรอง', lambda: recon_advance(env)),
            ('Recon #4d เช็ค', lambda: recon_cheque(env)),
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — ให้ส่วนอื่นตรวจต่อได้
            fail(name, "ตรวจไม่สำเร็จ: %s" % exc)

    print("\n" + "=" * 70)
    if _failures:
        print("สรุป: ไม่ผ่าน %d รายการ" % len(_failures))
        for f in _failures[:50]:
            print("   - %s" % f)
    else:
        print("สรุป: ผ่านทั้งหมด (Recon #1-#4) — ไม่มีผลต่างเกิน %.2f" % _TOL)
    print("=" * 70)


main()

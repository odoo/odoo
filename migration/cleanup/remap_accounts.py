# -*- coding: utf-8 -*-
"""ย้ายการอ้างอิงบัญชี OD15 (รหัส 6 หลัก) ไปยังบัญชี OD19 — COA Cleanup (odoo19_puat)

ที่มา: docs/od19_puat_account_mapping_20261105.xlsx (อนุมัติแล้ว 21/21 รายการ)

หลักการ:
    * เขียนข้อมูลผ่าน ORM เท่านั้น (ไม่ใช้ SQL ตรงสำหรับการเขียน)
    * ค่าเริ่มต้นเป็น DRY-RUN (อ่านอย่างเดียว) — ต้องตั้ง OD19_REMAP_CONFIRM=1 จึงเขียนจริง
    * แตะเฉพาะ "ค่าตั้งต้น/config" 3 กลุ่ม:
        1) ฟิลด์ Many2one ปกติที่ชี้มาที่บัญชีเดิม (journal default, res.company, tax, custom model)
        2) ฟิลด์ company_dependent (jsonb) ที่เก็บบัญชีเดิมไว้จริง
        3) ir.default (ค่าตั้งต้นระบบ) ที่ชี้มาที่บัญชีเดิม
      ไม่แตะรายการบัญชีที่ลงไว้แล้ว (posted entries) — ถ้าพบจะรายงานและข้าม
    * บัญชีเดิมไม่ถูกลบ — คงสถานะ Archive (active=False) ไว้
    * หมายเหตุ: ฟิลด์ company_dependent อย่าง res.partner.property_account_receivable_id
      ที่ ORM search เห็นเป็นค่า "fallback" (ไม่ได้เก็บในตาราง) จะไม่ถูกนับเป็น hit —
      ต้นเหตุจริงคือ ir.default ซึ่งจัดการในกลุ่มที่ 3

วิธีใช้ (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    # 1) ดูผลที่จะเกิดขึ้น (ไม่เขียนจริง)
    Get-Content -Raw migration\\cleanup\\remap_accounts.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http

    # 2) เขียนจริง (ต้องยืนยัน)
    $env:OD19_REMAP_CONFIRM = "1"
    Get-Content -Raw migration\\cleanup\\remap_accounts.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
    Remove-Item Env:\\OD19_REMAP_CONFIRM

ตัวแปรสภาพแวดล้อม:
    OD19_REMAP_CONFIRM=1   ยืนยันการเขียนจริง (ถ้าไม่ตั้ง = DRY-RUN)
"""
import os
import json

CONFIRM = os.environ.get('OD19_REMAP_CONFIRM', '') == '1'
DRY_RUN = not CONFIRM

# ---------------------------------------------------------------------------
# 1) ตารางจับคู่บัญชีเดิม -> บัญชีปลายทาง (ตาม Excel ที่อนุมัติแล้ว)
# ---------------------------------------------------------------------------
MAP = {
    "112100": "1130.00",
    "112101": "1130.00",
    "111100": "1111.00",
    "111102": "1111.01",
    "111207": "1112.01",
    "111208": "1114.02",
    "111209": "1113.01",
    "111210": "1113.02",
    "111211": "1114.01",
    "111212": "1112.02",
    "111214": "1113.03",
    "111215": "1113.04",
    "111216": "1112.03",
    "111217": "1114.03",
    "113100": "1140.01",
    "511100": "5110.00",
    "511200": "5120.00",
    "114200": "1151.01",
    "114300": "1153.04",
    "114400": "1153.01",
    "114401": "1153.05",
}

# บัญชีปลายทางที่ต้องสร้างใหม่ใน OD19 (ยังไม่มีในผังปัจจุบัน)
# หมายเหตุ: ชื่อไทยใช้ unicode escape เพื่อกันชื่อเสียหายเป็น '?' เมื่อรันผ่าน pipe/stdin
NEW_ACCOUNTS = {
    "1153.04": {"name": "\u0e20\u0e32\u0e29\u0e35\u0e40\u0e07\u0e34\u0e19\u0e44\u0e14\u0e49\u0e16\u0e39\u0e01\u0e2b\u0e31\u0e01\u0020\u0e13\u0020\u0e17\u0e35\u0e48\u0e08\u0e48\u0e32\u0e22",
                "account_type": "asset_current"},   # "ภาษีเงินได้ถูกหัก ณ ที่จ่าย"
    "1153.05": {"name": "\u0e20\u0e32\u0e29\u0e35\u0e2b\u0e31\u0e01\u0020\u0e13\u0020\u0e17\u0e35\u0e48\u0e08\u0e48\u0e32\u0e22\u0e23\u0e2d\u0e40\u0e04\u0e23\u0e14\u0e34\u0e15\u002f\u0e02\u0e2d\u0e04\u0e37\u0e19",
                "account_type": "asset_current"},   # "ภาษีหัก ณ ที่จ่ายรอเครดิต/ขอคืน"
}

# บัญชีเดิมที่คงสถานะ Archive ไว้ (ไม่ remap) — อ้างอิงตาม Excel ชีต "Keep Archived"
KEEP = [
    "511400", "511500", "511600", "511700",
    "212200", "212300", "212400",
    "114100", "114500",
    "113200", "113300", "113400", "113900", "112190",
    "111300", "111101", "111213",
]

# ---------------------------------------------------------------------------
# 2) การดำเนินการเพิ่มเติมตาม Excel (ชีต Summary)
# ---------------------------------------------------------------------------
# สมุดรายวันที่ต้อง Retire (archive) — journal PV เป็น placeholder ไม่มีรายการจริง
ARCHIVE_JOURNAL_CODES = ["PV"]

# หมวดสินค้าที่ต้องตั้งบัญชีค่าใช้จ่ายเริ่มต้น -> ต้นทุนบริการ (5120.00)
SERVICE_EXPENSE_CODE = "5120.00"
SERVICE_CATEGORY_NAMES = ["Services", "Expenses"]

# โมเดลธุรกรรม (posted entries) — ห้าม remap อัตโนมัติ ถ้าพบให้รายงานและข้าม
TRANSACTIONAL_MODELS = {
    'account.move', 'account.move.line', 'account.payment',
    'account.bank.statement.line', 'account.partial.reconcile',
    'account.full.reconcile', 'account.analytic.line', 'account.analytic.account',
}

_FIELDS_CACHE = None


def log(msg):
    print("REMAP| %s" % msg, flush=True)


def account_by_code(env, code, active_test=True):
    """ค้นบัญชีตามรหัส (ค่าเริ่มต้นรวมบัญชีที่ archive แล้ว)."""
    Acct = env['account.account'].sudo().with_context(active_test=active_test)
    return Acct.search([('code', '=', code)], limit=1)


def candidate_fields(env):
    """รายชื่อฟิลด์ FK ที่ชี้มาที่ account.account (stored many2one) — cache ไว้ใช้ซ้ำ."""
    global _FIELDS_CACHE
    if _FIELDS_CACHE is None:
        rows = env['ir.model.fields'].sudo().search_read(
            [('ttype', '=', 'many2one'),
             ('relation', '=', 'account.account'),
             ('store', '=', True)],
            ['model', 'name', 'company_dependent'])
        _FIELDS_CACHE = [r for r in rows if r['model'] in env]
    return _FIELDS_CACHE


def scan_references(env, old_codes):
    """สแกนหาการอ้างอิงบัญชีเดิมทั้ง 3 กลุ่ม — คืนรายการ hit (ยังไม่แก้อะไร).

    กลุ่มที่ 1: ฟิลด์ Many2one ปกติ (ผ่าน ORM search)
    กลุ่มที่ 2: ฟิลด์ company_dependent (jsonb) — อ่านค่าที่เก็บจริงด้วย SQL
    กลุ่มที่ 3: ir.default (ค่าตั้งต้นระบบ) — อ่านด้วย SQL
    """
    old_ids = list(old_codes)          # [account_id, ...]
    id_to_code = dict(old_codes)       # {account_id: code}
    fields = candidate_fields(env)
    hits = []

    # --- กลุ่มที่ 1: ฟิลด์ปกติ (ไม่ company_dependent) -----------------------
    scanned = 0
    for f in fields:
        if f['company_dependent']:
            continue
        model, fname = f['model'], f['name']
        Model = env[model].sudo()
        try:
            recs = Model.with_context(active_test=False).search_read(
                [(fname, 'in', old_ids)], ['id', fname])
            scanned += 1
            _collect(hits, 'field', model, fname, False, recs, id_to_code, None)
        except Exception:
            continue

    # --- กลุ่มที่ 2: company_dependent (jsonb) -------------------------------
    jsonb_hits = _scan_jsonb(env, fields, id_to_code)

    # --- กลุ่มที่ 3: ir.default ---------------------------------------------
    default_hits = _scan_ir_default(env, id_to_code)

    hits += jsonb_hits + default_hits
    log("สแกน: ฟิลด์ปกติ %d ครั้ง | jsonb(จริง) %d จุด | ir.default %d จุด → รวม %d จุด" % (
        scanned, len(jsonb_hits), len(default_hits), len(hits)))
    return hits


def _collect(hits, kind, model, fname, company_dependent, recs, id_to_code, company_id):
    """จัดกลุ่มผลลัพธ์ ORM เป็นรายการ hit (ต่อ 1 โมเดล/ฟิลด์/บัญชีเดิม)."""
    grouped = {}
    for r in recs:
        val = r.get(fname)
        if not val:
            continue
        # search_read คืนค่า many2one เป็น (id, display_name) — เอาเฉพาะ id
        target_id = val[0] if isinstance(val, (list, tuple)) else val
        grouped.setdefault(target_id, []).append(r['id'])
    for target_id, ids in grouped.items():
        hits.append({
            'kind': kind,
            'model': model,
            'field': fname,
            'company_dependent': company_dependent,
            'company_id': company_id,
            'old_id': target_id,
            'old_code': id_to_code.get(target_id, str(target_id)),
            'ids': ids,
        })


def _scan_jsonb(env, fields, id_to_code):
    """สแกนฟิลด์ company_dependent (jsonb) — นับเฉพาะค่าที่ "เก็บจริง" เท่านั้น.

    ค่าที่ ORM เห็นแต่ storage เป็น NULL คือ fallback จาก ir.default (กลุ่มที่ 3)
    จึงไม่นับที่นี่ เพื่อกัน false positive
    """
    old_ids = set(id_to_code)
    hits = []
    for f in fields:
        if not f['company_dependent']:
            continue
        model, fname = f['model'], f['name']
        if model not in env:
            continue
        table = env[model]._table
        try:
            env.cr.execute(
                'SELECT id, "%s" FROM "%s" WHERE "%s" IS NOT NULL' % (fname, table, fname))
            data = env.cr.fetchall()
        except Exception:
            continue
        grouped = {}
        for rid, val in data:
            if not isinstance(val, dict):
                continue
            for comp, v in val.items():
                if isinstance(v, int) and v in old_ids:
                    grouped.setdefault((int(comp), v), []).append(rid)
        for (comp, v), ids in grouped.items():
            hits.append({
                'kind': 'jsonb',
                'model': model,
                'field': fname,
                'company_dependent': True,
                'company_id': comp,
                'old_id': v,
                'old_code': id_to_code[v],
                'ids': ids,
            })
    return hits


def _scan_ir_default(env, id_to_code):
    """สแกน ir.default — เฉพาะฟิลด์ที่ relation = account.account."""
    old_ids = set(id_to_code)
    hits = []
    env.cr.execute("SELECT id, field_id, company_id, json_value FROM ir_default")
    rows = env.cr.fetchall()
    for rid, fid, comp, jval in rows:
        if not fid:
            continue
        fld = env['ir.model.fields'].browse(fid)
        if fld.relation != 'account.account':
            continue
        try:
            val = json.loads(jval) if isinstance(jval, str) else jval
        except Exception:
            continue
        vals = val if isinstance(val, list) else [val]
        for one in vals:
            if isinstance(one, int) and one in old_ids:
                hits.append({
                    'kind': 'ir.default',
                    'model': fld.model,
                    'field': fld.name,
                    'company_dependent': False,
                    'company_id': comp,
                    'old_id': one,
                    'old_code': id_to_code[one],
                    'ids': [rid],
                })
    return hits


def _describe(h):
    """ข้อความอธิบาย hit 1 รายการ (ใช้ใน log)."""
    comp = (" company=%d" % h['company_id']) if h['company_id'] else ""
    return "%s → %s | [%s] %s.%s%s | %d รายการ | ids=%s" % (
        h['old_code'], MAP.get(h['old_code'], '?'), h['kind'],
        h['model'], h['field'], comp, len(h['ids']), h['ids'])


def _apply_hit(env, h, new_id):
    """เขียนค่าใหม่ตามชนิดของ hit."""
    if h['kind'] == 'ir.default':
        env['ir.default'].set(h['model'], h['field'], new_id,
                              company_id=h['company_id'])
    elif h['kind'] == 'jsonb':
        env[h['model']].sudo().browse(h['ids']).with_company(
            h['company_id']).write({h['field']: new_id})
    else:  # ฟิลด์ปกติ
        env[h['model']].sudo().browse(h['ids']).with_context(
            active_test=False).write({h['field']: new_id})


def main():
    env = globals()['env']  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell
    dbname = env.cr.dbname
    log("ฐานข้อมูล: %s | โหมด: %s" % (dbname, "DRY-RUN (อ่านอย่างเดียว)" if DRY_RUN else "WRITE (เขียนจริง)"))

    # --- 0) สร้างบัญชีปลายทางใหม่ (ถ้ายังไม่มี) --------------------------------
    for code, meta in NEW_ACCOUNTS.items():
        existing = account_by_code(env, code, active_test=True)
        if existing:
            log("บัญชีปลายทาง %s มีอยู่แล้ว (id=%d) — ใช้ของเดิม" % (code, existing.id))
            continue
        if DRY_RUN:
            log("[DRY-RUN] จะสร้างบัญชีใหม่ %s (%s, %s)" % (code, meta['name'], meta['account_type']))
        else:
            acct = env['account.account'].sudo().create({
                'code': code,
                'name': meta['name'],
                'account_type': meta['account_type'],
                'company_ids': [(6, 0, env['res.company'].sudo().search([]).ids)],
            })
            log("สร้างบัญชีใหม่ %s (id=%d)" % (code, acct.id))

    # --- 1) หาบัญชีเดิมทุกตัว ------------------------------------------------
    old_accounts = {}
    for old_code in MAP:
        acct = account_by_code(env, old_code, active_test=False)
        if not acct:
            log("!! ไม่พบบัญชีเดิม %s — ข้าม" % old_code)
            continue
        old_accounts[acct.id] = old_code
    log("พบบัญชีเดิมที่จะ remap: %d/%d" % (len(old_accounts), len(MAP)))

    # ตรวจว่าบัญชีปลายทางมีจริงครบ
    for old_code, new_code in MAP.items():
        if not account_by_code(env, new_code, active_test=True):
            log("!! ไม่พบบัญชีปลายทาง %s (สำหรับ %s)" % (new_code, old_code))

    # --- 2) สแกนการอ้างอิง ---------------------------------------------------
    hits = scan_references(env, old_accounts)

    # --- 3) รายงานผลที่จะทำ --------------------------------------------------
    ok_hits = [h for h in hits if h['model'] not in TRANSACTIONAL_MODELS]
    tx_hits = [h for h in hits if h['model'] in TRANSACTIONAL_MODELS]
    log("จุดอ้างอิง config ที่จะย้าย: %d จุด | ธุรกรรม (ข้าม): %d จุด" % (len(ok_hits), len(tx_hits)))
    for h in sorted(hits, key=lambda x: (x['old_code'], x['kind'], x['model'])):
        tag = " [ธุรกรรม-ข้าม]" if h['model'] in TRANSACTIONAL_MODELS else ""
        log("  %s%s" % (_describe(h), tag))
    if not hits:
        log("  (ไม่พบการอ้างอิงคงเหลือ)")

    remaining = sorted({h['old_code'] for h in ok_hits})
    log("บัญชีเดิมที่ยังมีจุดอ้างอิง (config): %s" % (", ".join(remaining) if remaining else "—"))

    if DRY_RUN:
        log("DRY-RUN เสร็จ — ยังไม่แก้ข้อมูล (ตั้ง OD19_REMAP_CONFIRM=1 เพื่อเขียนจริง)")
        return

    # --- 4) remap จริง -------------------------------------------------------
    done_fields = 0
    for h in ok_hits:
        new_rec = account_by_code(env, MAP[h['old_code']], active_test=True)
        try:
            with env.cr.savepoint():
                _apply_hit(env, h, new_rec.id)
            done_fields += 1
        except Exception as exc:
            lines = str(exc).strip().splitlines()
            log("!! ย้ายไม่สำเร็จ %s.%s → %s: %s" % (
                h['model'], h['field'], MAP[h['old_code']], (lines[0] if lines else exc)[:180]))
    env.cr.commit()
    log("remap สำเร็จ %d/%d จุด" % (done_fields, len(ok_hits)))

    # --- 5) archive journal (Retire) ----------------------------------------
    for code in ARCHIVE_JOURNAL_CODES:
        jrn = env['account.journal'].sudo().search([('code', '=', code)])
        if not jrn:
            log("ไม่พบ journal %s — ข้าม" % code)
            continue
        jrn.write({'active': False})
        log("archive journal %s (%d รายการ)" % (code, len(jrn)))

    # --- 6) ตั้งค่าบัญชีค่าใช้จ่ายของหมวด Services/Expenses -> 5120.00 -------
    service_acct = account_by_code(env, SERVICE_EXPENSE_CODE, active_test=True)
    if not service_acct:
        log("!! ไม่พบบัญชี %s — ข้ามการตั้งค่าหมวดสินค้า" % SERVICE_EXPENSE_CODE)
    else:
        for company in env['res.company'].sudo().search([]):
            cats = env['product.category'].sudo().with_company(company).search(
                [('name', 'in', SERVICE_CATEGORY_NAMES)])
            if cats:
                cats.with_company(company).write(
                    {'property_account_expense_categ_id': service_acct.id})
                log("ตั้งค่า %s → %s (company=%s, %d หมวด)" % (
                    "/".join(SERVICE_CATEGORY_NAMES), SERVICE_EXPENSE_CODE,
                    company.name, len(cats)))
    env.cr.commit()

    # --- 7) ตรวจสอบหลังทำ ----------------------------------------------------
    left = scan_references(env, old_accounts)
    left_ok = [h for h in left if h['model'] not in TRANSACTIONAL_MODELS]
    log("หลัง remap — จุดอ้างอิง config คงเหลือ: %d จุด" % len(left_ok))
    for h in left_ok:
        log("  คงเหลือ: %s" % _describe(h))
    log("เสร็จสิ้น (CONFIRM=1)")


main()

# -*- coding: utf-8 -*-
r"""sim_report_parity — ตรวจว่า "รายงาน" ของ od19 ให้ผลตรงกับ od15

แนวคิด
    ถ้ายอด NET (debit-credit) ต่อบัญชี ตรงกันทุกบัญชี และการจัดกลุ่มตามประเภท
    บัญชี (asset/liability/equity/income/expense) ตรงกันแล้ว
    งบทดลอง / งบกำไรขาดทุน (P&L) / งบดุล (Balance Sheet) / รายงานภาษี
    ที่คำนวณจากยอดสุทธิ จะออกมาตรงกันโดยอัตโนมัติ

การเปรียบเทียบ (ช่วงเดียวกัน REP_D1..REP_D2)
    1) NET ต่อบัญชี (od15 code -> od19 code) — ต้อง diff = 0
    2) ยอดรวมตามกลุ่มรายงาน (BS: asset/liability/equity, PL: income/expense)
    3) ยอดลูกหนี้/เจ้าหนี้ (AR/AP) แยกตามคู่ค้า

วิธีรัน (จาก root โปรเจกต์):
    Get-Content -LiteralPath .\migration\simulate\sim_report_parity.py -Raw |
        .\venv19\Scripts\python.exe -u .\odoo-bin shell -c .\odoo.conf `
        -d odoo19_puat --no-http --db-filter=^odoo19_puat$

ตัวแปรสภาพแวดล้อม
    REP_D1 / REP_D2   ช่วงวันที่ (ค่าเริ่มต้น 2026-01-01 .. 2026-08-31)
    PAR_TOP           จำนวนแถวที่แสดงต่อส่วน (ค่าเริ่มต้น 40)
"""
import os
import sys


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


D1 = os.environ.get('REP_D1', '2026-01-01')
D2 = os.environ.get('REP_D2', '2026-08-31')
TOP = int(os.environ.get('PAR_TOP', '40') or '40')

AMAP = {k: (v.get('รหัส Odoo 19') or '').strip()
        for k, v in common.load_map('od15_code_to_od19_code.csv').items()}

REPORT_BUCKET = {
    'asset': 'งบดุล:สินทรัพย์',
    'liability': 'งบดุล:หนี้สิน',
    'equity': 'งบดุล:ส่วนของผู้ถือหุ้น',
    'income': 'P&L:รายได้',
    'expense': 'P&L:ค่าใช้จ่าย',
}


def _bucket(account_type):
    at = account_type or ''
    for pre, name in REPORT_BUCKET.items():
        if at.startswith(pre):
            return name
    return 'อื่นๆ (%s)' % (at or '?')


def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    common.set_step('parity')
    common.log("ตรวจ parity รายงาน od15 vs od19 ช่วง %s .. %s" % (D1, D2))

    # od19: code -> account_type (ใช้จำแนกกลุ่มรายงานทั้งสองฝั่ง)
    od19_accs = env['account.account'].search_read(  # noqa: F821
        [], ['code', 'account_type', 'name'])
    type_by_code = {a['code']: a['account_type'] for a in od19_accs}

    # ---- 1) NET ต่อบัญชี -------------------------------------------------
    # od15 -> (od19 code) -> [dr, cr]
    exp = {}
    for r in legacy.fetch_all(
            "SELECT a.code AS code, sum(l.debit) AS dr, sum(l.credit) AS cr "
            "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
            "JOIN account_account a ON a.id=l.account_id "
            "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
            "GROUP BY 1", {'d1': D1, 'd2': D2}):
        code19 = AMAP.get(r['code']) or ('??%s' % r['code'])
        v = exp.setdefault(code19, [0.0, 0.0])
        v[0] += float(r['dr'] or 0.0)
        v[1] += float(r['cr'] or 0.0)

    # od19
    recs = env['account.move.line'].search_read(  # noqa: F821
        [('parent_state', '=', 'posted'), ('date', '>=', D1), ('date', '<=', D2)],
        ['account_id', 'debit', 'credit'])
    acc_ids = set(r['account_id'][0] for r in recs if r['account_id'])
    code_by_id = {a['id']: a['code'] for a in env['account.account'].browse(  # noqa: F821
        list(acc_ids)).read(['code'])}
    got = {}
    for r in recs:
        aid = r['account_id'][0] if r['account_id'] else None
        code19 = code_by_id.get(aid, '??')
        v = got.setdefault(code19, [0.0, 0.0])
        v[0] += float(r['debit'] or 0.0)
        v[1] += float(r['credit'] or 0.0)

    allk = sorted(set(exp) | set(got))
    diff_rows = []
    for c in allk:
        e = exp.get(c, [0.0, 0.0])
        g = got.get(c, [0.0, 0.0])
        e_net = round(e[0] - e[1], 2)
        g_net = round(g[0] - g[1], 2)
        if abs(round(g_net - e_net, 2)) >= 0.05:
            diff_rows.append((abs(g_net - e_net), c, e_net, g_net))

    common.log("== 1) NET ต่อบัญชี (od15 vs od19) ==")
    common.log("   บัญชีทั้งหมด: %d | ไม่ตรง (NET): %d" % (len(allk), len(diff_rows)))
    diff_rows.sort(reverse=True)
    for _, c, e, g in diff_rows[:TOP]:
        common.log("     %-12s od15 NET=%16.2f od19 NET=%16.2f diff=%14.2f"
                   % (c, e, g, g - e))

    # ---- 2) ยอดรวมตามกลุ่มรายงาน ----------------------------------------
    b_exp = {}
    b_got = {}
    for c in allk:
        b = _bucket(type_by_code.get(c))
        e = exp.get(c, [0.0, 0.0])
        g = got.get(c, [0.0, 0.0])
        # มุมมองงบดุล/PL ใช้ NET (dr-cr): สินทรัพย์/ค่าใช้จ่าย = +, หนี้สิน/ทุน/รายได้ = -
        b_exp[b] = b_exp.get(b, 0.0) + (e[0] - e[1])
        b_got[b] = b_got.get(b, 0.0) + (g[0] - g[1])
    common.log("== 2) ยอดรวมตามกลุ่มรายงาน (NET) ==")
    for b in sorted(set(b_exp) | set(b_got)):
        e = round(b_exp.get(b, 0.0), 2)
        g = round(b_got.get(b, 0.0), 2)
        flag = '' if abs(round(g - e, 2)) < 0.05 else '  <-- ต่าง'
        common.log("   %-26s od15=%18.2f od19=%18.2f diff=%14.2f%s"
                   % (b, e, g, round(g - e, 2), flag))

    # ---- 3) AR/AP แยกตามคู่ค้า -------------------------------------------
    ar_ap_types = ('asset_receivable', 'liability_payable')
    ap_codes = [c for c in type_by_code if type_by_code[c] in ar_ap_types]
    ar_ap_ids = [a['id'] for a in od19_accs if a['account_type'] in ar_ap_types]
    # od15 (กรองเฉพาะบัญชี AR/AP)
    p_exp = {}
    for r in legacy.fetch_all(
            "SELECT a.code AS code, rp.name AS partner, "
            "       sum(l.debit) AS dr, sum(l.credit) AS cr "
            "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
            "JOIN account_account a ON a.id=l.account_id "
            "LEFT JOIN res_partner rp ON rp.id=l.partner_id "
            "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
            "GROUP BY 1,2", {'d1': D1, 'd2': D2}):
        code19 = AMAP.get(r['code'] or '')
        if code19 not in ap_codes:
            continue
        key = (r['partner'] or '(ไม่มีคู่ค้า)').strip()
        v = p_exp.setdefault(key, 0.0)
        p_exp[key] = v + (float(r['dr'] or 0.0) - float(r['cr'] or 0.0))

    # od19
    p_got = {}
    for r in env['account.move.line'].search_read(  # noqa: F821
            [('parent_state', '=', 'posted'), ('date', '>=', D1), ('date', '<=', D2),
             ('account_id', 'in', ar_ap_ids)],
            ['partner_id', 'debit', 'credit']):
        key = (r['partner_id'][1] if r['partner_id'] else '(ไม่มีคู่ค้า)').strip()
        p_got[key] = p_got.get(key, 0.0) + (float(r['debit'] or 0.0) - float(r['credit'] or 0.0))

    p_all = sorted(set(p_exp) | set(p_got))
    p_diff = []
    for k in p_all:
        e = round(p_exp.get(k, 0.0), 2)
        g = round(p_got.get(k, 0.0), 2)
        if abs(round(g - e, 2)) >= 0.05:
            p_diff.append((abs(g - e), k, e, g))
    p_diff.sort(reverse=True)
    common.log("== 3) ลูกหนี้/เจ้าหนี้ (AR/AP) แยกตามคู่ค้า (NET) ==")
    common.log("   คู่ค้าที่มียอด: %d | ไม่ตรง: %d" % (len(p_all), len(p_diff)))
    for _, k, e, g in p_diff[:TOP]:
        common.log("     %-40s od15=%16.2f od19=%16.2f diff=%14.2f"
                   % (k[:40], e, g, g - e))

    # ---- สรุป ------------------------------------------------------------
    ok = (not diff_rows) and (not p_diff) and \
        all(abs(round(b_got.get(b, 0.0) - b_exp.get(b, 0.0), 2)) < 0.05
            for b in set(b_exp) | set(b_got))
    common.log("== สรุป ==")
    common.log("   NET ต่อบัญชีไม่ตรง: %d | AR/AP ไม่ตรง: %d | ผลลัพธ์: %s"
               % (len(diff_rows), len(p_diff), 'ผ่าน (ตรงกัน)' if ok else 'ยังมีผลต่าง'))


main()

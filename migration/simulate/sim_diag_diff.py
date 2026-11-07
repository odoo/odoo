# -*- coding: utf-8 -*-
r"""sim_diag_diff — วินิจฉัยผลต่างงบทดลอง (od15 vs od19) หลัง replicate

เป้าหมาย
    หาว่าบัญชีใด/เดือนใดที่ทำให้ยอดรวม dr/cr ต่างกัน (ไม่ใช่แค่ net)
    แล้วจัดอันดับผู้ที่ทำให้ผลต่างมากที่สุด เพื่อสืบหาต้นเหตุ

วิธีรัน (จาก root โปรเจกต์):
    Get-Content -LiteralPath .\migration\simulate\sim_diag_diff.py -Raw |
        .\venv19\Scripts\python.exe -u .\odoo-bin shell -c .\odoo.conf `
        -d odoo19_puat --no-http --db-filter=^odoo19_puat$

ตัวแปรสภาพแวดล้อม
    REP_D1 / REP_D2   ช่วงวันที่ (ค่าเริ่มต้น 2026-01-01 .. 2026-08-31)
    DIAG_TOP          จำนวนแถวที่แสดงต่อส่วน (ค่าเริ่มต้น 30)
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
TOP = int(os.environ.get('DIAG_TOP', '30') or '30')

AMAP = {k: (v.get('รหัส Odoo 19') or '').strip()
        for k, v in common.load_map('od15_code_to_od19_code.csv').items()}


def main():
    common.init(env)  # noqa: F821
    _bootstrap_od15_env()
    common.set_step('diag')
    common.log("วินิจฉัยผลต่างงบทดลอง %s .. %s" % (D1, D2))

    # od15: ต่อ (ym, code15) -> [dr, cr]
    rows = legacy.fetch_all(
        "SELECT to_char(m.date,'YYYY-MM') AS ym, a.code AS code, "
        "       sum(l.debit) AS dr, sum(l.credit) AS cr "
        "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
        "JOIN account_account a ON a.id=l.account_id "
        "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
        "GROUP BY 1,2", {'d1': D1, 'd2': D2})
    exp = {}
    for r in rows:
        code19 = AMAP.get(r['code']) or ('??%s' % r['code'])
        v = exp.setdefault((r['ym'], code19), [0.0, 0.0, 0.0])
        v[0] += float(r['dr'] or 0.0)
        v[1] += float(r['cr'] or 0.0)
        v[2] += float(r['dr'] or 0.0) - float(r['cr'] or 0.0)

    # od19
    recs = env['account.move.line'].search_read(  # noqa: F821
        [('parent_state', '=', 'posted'), ('date', '>=', D1), ('date', '<=', D2)],
        ['account_id', 'debit', 'credit', 'date'])
    acc_ids = set(r['account_id'][0] for r in recs if r['account_id'])
    code_by_id = {a['id']: a['code'] for a in env['account.account'].browse(  # noqa: F821
        list(acc_ids)).read(['code'])}
    got = {}
    for r in recs:
        aid = r['account_id'][0] if r['account_id'] else None
        code19 = code_by_id.get(aid, '??')
        ym = str(r['date'])[:7]
        v = got.setdefault((ym, code19), [0.0, 0.0, 0.0])
        v[0] += float(r['debit'] or 0.0)
        v[1] += float(r['credit'] or 0.0)
        v[2] += float(r['debit'] or 0.0) - float(r['credit'] or 0.0)

    allk = sorted(set(exp) | set(got))
    # 1) แถวที่ dr ต่าง (เรียงตามขนาด)
    by_dr = []
    by_cr = []
    for k in allk:
        e = exp.get(k, [0.0, 0.0, 0.0])
        g = got.get(k, [0.0, 0.0, 0.0])
        ddr = round(g[0] - e[0], 2)
        dcr = round(g[1] - e[1], 2)
        if abs(ddr) >= 0.05:
            by_dr.append((abs(ddr), k[0], k[1], round(e[0], 2), round(g[0], 2), ddr))
        if abs(dcr) >= 0.05:
            by_cr.append((abs(dcr), k[0], k[1], round(e[1], 2), round(g[1], 2), dcr))
    by_dr.sort(reverse=True)
    by_cr.sort(reverse=True)

    common.log("== เดบิตต่าง (dr) ==")
    common.log("   แถวที่ต่าง: %d | ผลรวม |diff| = %.2f"
               % (len(by_dr), sum(x[0] for x in by_dr)))
    for a, ym, code, e, g, d in by_dr[:TOP]:
        common.log("   %s %-12s od15=%14.2f od19=%14.2f diff=%12.2f" % (ym, code, e, g, d))

    common.log("== เครดิตต่าง (cr) ==")
    common.log("   แถวที่ต่าง: %d | ผลรวม |diff| = %.2f"
               % (len(by_cr), sum(x[0] for x in by_cr)))
    for a, ym, code, e, g, d in by_cr[:TOP]:
        common.log("   %s %-12s od15=%14.2f od19=%14.2f diff=%12.2f" % (ym, code, e, g, d))

    # 2) สรุปต่อเดือน (dr/cr รวม)
    months = sorted(set(k[0] for k in allk))
    common.log("== สรุปต่อเดือน (dr/cr รวม) ==")
    for ym in months:
        e_dr = sum(v[0] for k, v in exp.items() if k[0] == ym)
        e_cr = sum(v[1] for k, v in exp.items() if k[0] == ym)
        g_dr = sum(v[0] for k, v in got.items() if k[0] == ym)
        g_cr = sum(v[1] for k, v in got.items() if k[0] == ym)
        common.log("   %s | dr diff=%12.2f | cr diff=%12.2f"
                   % (ym, round(g_dr - e_dr, 2), round(g_cr - e_cr, 2)))

    # 3) สรุปต่อบัญชี (รวมทุกเดือน, ใช้ dr/cr แยก)
    acct_dr = {}
    acct_cr = {}
    for k in allk:
        e = exp.get(k, [0.0, 0.0, 0.0])
        g = got.get(k, [0.0, 0.0, 0.0])
        acct_dr[k[1]] = acct_dr.get(k[1], 0.0) + (g[0] - e[0])
        acct_cr[k[1]] = acct_cr.get(k[1], 0.0) + (g[1] - e[1])
    common.log("== ผลต่างสะสมต่อบัญชี (dr diff / cr diff) ==")
    comb = []
    for c in sorted(set(acct_dr) | set(acct_cr)):
        ddr = round(acct_dr.get(c, 0.0), 2)
        dcr = round(acct_cr.get(c, 0.0), 2)
        if abs(ddr) >= 0.05 or abs(dcr) >= 0.05:
            comb.append((abs(ddr) + abs(dcr), c, ddr, dcr))
    comb.sort(reverse=True)
    for _, c, ddr, dcr in comb[:TOP]:
        common.log("   %-12s dr diff=%14.2f cr diff=%14.2f" % (c, ddr, dcr))
    common.log("   รวมบัญชีที่มีผลต่าง: %d" % len(comb))


main()

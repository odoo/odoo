# -*- coding: utf-8 -*-
r"""_probe_wht — สืบหาว่าบรรทัดบัญชี WHT (2211.01/2211.02) ใน od15 หายไปตอน replicate

วิธีรัน:
    Get-Content -LiteralPath .\migration\simulate\_probe_wht.py -Raw |
        .\venv19\Scripts\python.exe -u .\odoo-bin shell -c .\odoo.conf `
        -d odoo19_puat --no-http --db-filter=^odoo19_puat$
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
    raise RuntimeError("ไม่พบโฟลเดอร์ migration/import")


_ID = _bootstrap_import_dir()
if _ID not in sys.path:
    sys.path.insert(0, _ID)
import common  # noqa: E402
import legacy  # noqa: E402


def _bootstrap_od15_env():
    if os.environ.get('OD15_PASSWORD'):
        return
    conf = os.path.join(os.getcwd(), 'odoo.conf')
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


common.init(env)  # noqa: F821
_bootstrap_od15_env()
common.set_step('probe.wht')

# 1) od15: บรรทัดบัญชี VAT (รหัส od15 = 2211-01/2211-02/1151-01/1151-02)
#    แยกตาม move_type + มี tax_line_id หรือไม่
rows = legacy.fetch_all(
    "SELECT a.code AS code, m.move_type AS mt, "
    "       (l.tax_line_id IS NOT NULL) AS istax, "
    "       (SELECT name FROM account_tax WHERE id=l.tax_line_id) AS tname, "
    "       count(*) AS n, sum(l.debit) AS dr, sum(l.credit) AS cr "
    "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
    "JOIN account_account a ON a.id=l.account_id "
    "WHERE m.state='posted' AND m.date BETWEEN %(d1)s AND %(d2)s "
    "  AND a.code IN ('2211-01','2211-02','1151-01','1151-02') "
    "GROUP BY 1,2,3,4 ORDER BY 1,2,3,4", {'d1': '2026-01-01', 'd2': '2026-08-31'})
common.log("od15 VAT accounts แยกตาม move_type / istax / ชื่อภาษี:")
for r in rows:
    common.log("   %-8s %-12s istax=%-5s %-38s n=%5s dr=%14.2f cr=%14.2f"
               % (r['code'], r['mt'], r['istax'], (r['tname'] or '-')[:38], r['n'],
                  float(r['dr'] or 0), float(r['cr'] or 0)))

# 2) od15: ตัวอย่าง move ที่กระทบ 2211-01 (output VAT) ในเม.ย. มากสุด
common.log("-- ตัวอย่าง od15 move (เม.ย. 2026) ที่กระทบ 2211-01 --")
mv = legacy.fetch_all(
    "SELECT m.id, m.name, m.move_type, m.date, j.code AS jcode "
    "FROM account_move_line l JOIN account_move m ON m.id=l.move_id "
    "JOIN account_account a ON a.id=l.account_id "
    "JOIN account_journal j ON j.id=m.journal_id "
    "WHERE m.state='posted' AND a.code='2211-01' AND m.date >= '2026-04-01' AND m.date <= '2026-04-30' "
    "ORDER BY l.debit DESC LIMIT 3", {})
for m in mv:
    common.log("   move id=%s %s %s %s j=%s" % (m['id'], m['name'], m['move_type'], m['date'], m['jcode']))
    ls = legacy.fetch_all(
        "SELECT a.code AS code, l.name, l.debit, l.credit, l.display_type, "
        "       (SELECT name FROM account_tax WHERE id=l.tax_line_id) AS tname "
        "FROM account_move_line l JOIN account_account a ON a.id=l.account_id "
        "WHERE l.move_id=%(mid)s ORDER BY l.id", {'mid': m['id']})
    for l in ls:
        common.log("      %-10s dr=%10.2f cr=%10.2f %-12s tax=%s"
                   % (l['code'], float(l['debit'] or 0), float(l['credit'] or 0),
                      (l['display_type'] or '')[:12], l['tname'] or '-'))
    xmlid = common.get_xmlid('account.move', 'gl15rep_%s' % m['id'])
    mid19 = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)  # noqa: F821
    if not mid19:
        common.log("      -> od19: ไม่พบ (external id %s)" % xmlid)
        continue
    mv19 = env['account.move'].browse(mid19)  # noqa: F821
    common.log("      -> od19 id=%s %s state=%s" % (mv19.id, mv19.name, mv19.state))
    for l in mv19.line_ids.sorted('id'):
        common.log("         %-10s dr=%10.2f cr=%10.2f %-12s tax=%s"
                   % (l.account_id.code, l.debit, l.credit,
                      (l.display_type or '')[:12], l.tax_line_id.name or '-'))
common.log("probe.wht เสร็จสิ้น")

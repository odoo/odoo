# -*- coding: utf-8 -*-
r"""Gate 6 — ตรวจความต่อเนื่องของเลขรัน (Sequence) Odoo 15 -> Odoo 19

วิธีรัน (จาก root ของโปรเจกต์):

    $env:PYTHONIOENCODING="utf-8"
    Get-Content migration\recon\sequence_check.py -Raw | `
        & .\venv19\Scripts\python.exe -u .\odoo-bin shell -c odoo.conf -d odoo19_puat --no-http `
        *> migration\recon\sequence_check.log

ตรวจ 2 เรื่อง (ตามแผน Phase 6):
    6.1/6.4  เลขถัดไปของ sequence ปลายทางต้อง >= เลข effective ของระบบเดิม
             (ค่า effective = next ที่ระบบเดิมจะออกถัดไป) -> เอกสารใหม่จะไม่ทับเลขเดิม
    6.2      แสดงเลขที่จะออกถัดไปต่อชนิดเอกสาร (ไม่ consume เลข: อ่านค่าพยากรณ์)

หลักการทำงาน (อ่านอย่างเดียว 100% — ไม่แก้ข้อมูล):
    * อ่าน sequence ระบบเดิมผ่าน legacy.py (read-only)
    * จับคู่กับ Odoo 19 ด้วย migration/mapping/sequence_map.csv
    * เทียบค่า number_next ปลายทาง (รองรับ use_date_range) กับ effective ต้นทาง
"""
import os
import sys

# ---- ผูก sys.path ให้หา migration/import ได้ (เหมือน recon/run.py) ----
# หมายเหตุ: ใน `odoo shell` ตัวแปร __file__ ไม่มี จึงหาโฟลเดอร์จาก cwd แทน
_here = os.getcwd()
for _ in range(6):
    _cand = os.path.join(_here, 'migration', 'import')
    if os.path.isfile(os.path.join(_cand, 'common.py')):
        sys.path.insert(0, _cand)
        break
    _parent = os.path.dirname(_here)
    if _parent == _here:
        break
    _here = _parent

import common  # noqa: E402
import legacy  # noqa: E402
from steps import s09_sequences  # noqa: E402

_TOL = 0


def _next_of(seq):
    """คืนค่าเลขถัดไปจริงของ sequence (รองรับ use_date_range)."""
    target = seq._get_current_sequence() if seq.use_date_range else seq
    return target.number_next or 1


def run(env):
    print("=" * 70)
    print("Gate 6: ตรวจความต่อเนื่องของเลขรัน (Sequence) — Odoo 19 (odoo19_puat) เทียบ Odoo 15")
    print("=" * 70)

    legacy_rows = s09_sequences._fetch_legacy_effective()
    mapping = common.load_map(s09_sequences.MAP_FILE)

    ok = 0
    low = []          # ต่ำกว่า legacy -> เสี่ยงเลขชน
    notfound = []
    skipped_used = []  # 'skip' แต่ระบบเดิมเคยออกเลขแล้ว (ยังไม่มีคู่ใน OD19)
    seen = set()

    print("\n=== 6.1/6.4: เทียบเลขถัดไป (OD19) กับ effective (OD15) ===")
    print("%-30s %9s %-34s %11s %s" % ("od15_prefix", "eff", "od19 (match/value)", "od19_next", "ผล"))
    for row in sorted(legacy_rows, key=lambda r: -(r.get('eff') or 0)):
        prefix = (row.get('prefix') or '').strip()
        eff = row.get('eff') or 0
        if eff <= 1 or not prefix:
            continue
        seen.add(prefix)
        m = mapping.get(prefix)
        if not m:
            notfound.append("%s (eff=%d, ไม่มีแถวใน sequence_map.csv)" % (prefix, eff))
            continue
        match = (m.get('od19_match') or '').strip()
        value = (m.get('od19_value') or '').strip()
        if match == 'skip':
            skipped_used.append("%s eff=%d — %s" % (prefix, eff, (m.get('note') or '')))
            continue
        seq = s09_sequences._find_sequence(match, value)
        if not seq:
            notfound.append("%s -> %s=%s (ไม่พบ sequence ปลายทาง)" % (prefix, match, value))
            continue
        next19 = _next_of(seq)
        result = "OK" if next19 >= eff else "เสี่ยงชน!"
        if next19 >= eff:
            ok += 1
        else:
            low.append("%s: od19_next=%d < eff=%d" % (prefix, next19, eff))
        print("%-30s %9d %-34s %11d %s" % (prefix, eff, match + "=" + value, next19, result))

    print("\n=== 6.2: เลขที่จะออกถัดไปต่อชนิดเอกสาร (พยากรณ์ ไม่ consume เลข) ===")
    docs = (
        ('ใบเสนอราคา TA', 'sale.quotation.ta'),
        ('ใบเสนอราคา IA', 'sale.quotation.ia'),
        ('ใบสั่งซื้อ TA', 'purchase.order.ta'),
        ('ใบสั่งซื้อ IA', 'purchase.order.ia'),
        ('ใบสำคัญจ่าย-ซื้อ (PVV)', 'account.voucher.vendor.bills'),
        ('ใบสำคัญจ่ายผู้ขาย (PV)', 'account.voucher.vendor.payment'),
        ('ใบสำคัญรับเงิน (RV)', 'account.voucher.customer.payment'),
        ('ใบสำคัญเงินสด (CAV)', 'account.voucher.cash'),
        ('ภาษีซื้อ ภ.พ.30 (VATP)', 'account.vat.purchase'),
        ('ภาษีขาย ภ.พ.30 (VATS)', 'account.vat.sale'),
        ('หนังสือรับรอง ภ.ง.ด.53', 'account.wht53'),
        ('ใบเบิกล่วงหน้า (PP)', 'account.prepayment'),
    )
    for label, code in docs:
        seq = env['ir.sequence'].search([('code', '=', code)], limit=1)
        if not seq:
            print("  %-28s (ไม่พบ sequence code=%s)" % (label, code))
            continue
        try:
            plan = seq.get_next_char(_next_of(seq))
        except Exception as exc:  # noqa: BLE001
            plan = "(คำนวณไม่ได้: %s)" % exc
        print("  %-28s %s" % (label, plan))

    print("\n=== เอกสารที่ OD19 ออกเลขแล้ว (account.move) ===")
    moves = env['account.move'].search([], order='id')
    print("  ทั้งหมด %d ใบ | ตัวอย่างชื่อ: %s" % (
        len(moves), ', '.join(moves[:5].mapped('name')) or '-'))

    print("\n" + "=" * 70)
    print("สรุป Gate 6")
    print("  ตรวจ sequence ที่มีคู่: %d รายการ | ผ่าน %d | ต่ำกว่า legacy %d" % (
        ok + len(low), ok, len(low)))
    if low:
        for line in low:
            print("  [FAIL] %s" % line)
    if notfound:
        print("  [หมายเหตุ] ไม่มีแถว/ไม่พบปลายทาง %d รายการ:" % len(notfound))
        for line in notfound:
            print("    - %s" % line)
    if skipped_used:
        print("  [หมายเหตุ] 'skip' แต่ระบบเดิมเคยออกเลขแล้ว %d รายการ (ยังไม่มีคู่ใน OD19 — รอการยืนยัน):"
              % len(skipped_used))
        for line in skipped_used:
            print("    - %s" % line)
    verdict = "ผ่าน" if not low else "ไม่ผ่าน"
    print("  ผล: %s" % verdict)
    print("=" * 70)
    return not low


run(env)  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell

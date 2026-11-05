# -*- coding: utf-8 -*-
r"""รายงานความครอบคลุมการนำเข้า (Import Coverage) — Odoo 19 (odoo19_puat)

นับจำนวนเรกคอร์ดที่นำเข้าจาก Odoo 15 (module='__import15__') แยกตามโมเดลปลายทาง
เพื่อยืนยันว่า "นำเข้าข้อมูลครบทุกโมดูล" และรันซ้ำได้ (idempotent)

วิธีรัน (จาก root ของโปรเจกต์ c:\odoo-dev\odoo19):
    $env:PYTHONIOENCODING="utf-8"
    Get-Content migration\recon\import_coverage.py -Raw |
        & .\venv19\Scripts\python.exe -u .\odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
"""
import os
import sys

# ---- ผูก sys.path ให้หา migration/import ได้ (__file__ ใช้ไม่ได้ใน odoo shell) ----
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


# โมเดลปลายทางที่คาดหวัง (ตาม step s01..s10) พร้อมคำอธิบายไทย
# หมายเหตุ: ภาษี (s02) เป็นการ "จับคู่" กับรายการที่ Odoo 19 มีอยู่แล้ว ไม่ได้สร้างใหม่
#           ยอดยกมาสต็อก (s08) ใช้วิธี periodic valuation + stock.quant (ไม่สร้าง
#           stock.valuation.layer) ตามที่อนุมัติ จึงไม่มี External ID บนโมเดลนั้น
EXPECTED = [
    ('s01', 'account.account', 'ผังบัญชี'),
    ('s02', 'account.journal', 'สมุดรายวัน'),
    ('s02', 'account.payment.term', 'เงื่อนไขชำระ'),
    ('s02', 'uom.uom', 'หน่วยนับ'),
    ('s02', 'product.pricelist', 'นโยบายราคา'),
    ('s03', 'res.partner', 'คู่ค้า/ผู้ติดต่อ'),
    ('s04', 'product.template', 'สินค้า/บริการ'),
    ('s04', 'product.pricelist.item', 'รายการราคา'),
    ('s05', 'od19.sale.term.template', 'เงื่อนไขขาย (master)'),
    ('s05', 'od19.purchase.term.template', 'เงื่อนไขซื้อ (master)'),
    ('s06', 'hr.department', 'แผนก'),
    ('s06', 'hr.job', 'ตำแหน่งงาน'),
    ('s06', 'res.users', 'ผู้ใช้'),
    ('s06', 'hr.employee', 'พนักงาน'),
    ('s07', 'project.project', 'โครงการ/Job No.'),
    ('s08', 'account.move', 'ยอดยกมา (AR/AP/GL)'),
    ('s08', 'account.asset.profile', 'หมวดหมู่สินทรัพย์'),
    ('s08', 'account.asset', 'สินทรัพย์ถาวร'),
    ('s08', 'account.cheque', 'เช็ค'),
    ('s08', 'withholding.tax.cert', 'ใบรับรองหัก ณ ที่จ่าย'),
    ('s08', 'account.advance', 'เงินจ่ายล่วงหน้า'),
    ('s10', 'ir.attachment', 'ไฟล์แนบ'),
]


def run(env):
    print("=" * 78)
    print("Import Coverage — Odoo 19 (odoo19_puat) | module='__import15__'")
    print("=" * 78)

    # นับรวมทั้งโมดูล
    total = env['ir.model.data'].search_count([('module', '=', common.MODULE_PREFIX)])
    print("รวม External ID ทั้งหมด: %s รายการ" % format(total, ','))

    # นับตามโมเดล (ใช้ _read_group) — model เก็บเป็นชื่อโมเดลปลายทาง
    grouped = env['ir.model.data']._read_group(
        [('module', '=', common.MODULE_PREFIX)],
        groupby=['model'], aggregates=['__count'])
    counts = {m: c for m, c in grouped}

    print("-" * 78)
    print("%-4s %-30s %-26s %10s" % ('step', 'model', 'คำอธิบาย', 'จำนวน'))
    print("-" * 78)
    missing = []
    for step, model, desc in EXPECTED:
        n = counts.get(model)
        shown = format(n, ',') if n else '—'
        flag = '' if n else '  <== ไม่พบ'
        if not n:
            missing.append((model, desc))
        print("%-4s %-30s %-26s %10s%s" % (step, model, desc, shown, flag))

    print("-" * 78)
    print("โมเดลที่คาดหวังแต่ไม่พบ: %s" % (len(missing) or 'ไม่มี'))

    # โมเดลปลายทางทั้งหมดที่มีการนำเข้า (เรียงจากมากไปน้อย)
    print("-" * 78)
    print("โมเดลปลายทางทั้งหมด (%d โมเดล) เรียงตามจำนวน:" % len(counts))
    for m, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("  %-40s %10s" % (m, format(c, ',')))

    print("=" * 78)
    print("สรุป: External ID รวม %s | โมเดล %d | คาดหวังไม่พบ %d"
          % (format(total, ','), len(counts), len(missing)))
    print("=" * 78)


run(env)  # noqa: F821

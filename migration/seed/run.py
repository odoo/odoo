# -*- coding: utf-8 -*-
"""run.py — ตัวรันชุดสร้างข้อมูลตัวอย่าง Odoo 19 ผ่าน `odoo shell`

วิธีใช้ (PowerShell):
    Get-Content -LiteralPath .\migration\seed\run.py -Raw |
        .\venv19\Scripts\python.exe .\odoo-bin shell -c .\odoo.conf -d odoo19_pdev --no-http

ตัวแปรสภาพแวดล้อมที่รองรับ:
    SEED_ONLY=s10_partners,s20_products   เลือกรันเฉพาะบาง section
    SEED_DRY_RUN=1                        ไม่เขียนข้อมูลจริง
    SEED_VERBOSE_ERROR=1                  พิมพ์ traceback ของ record ที่ล้มเหลว
"""
import os
import sys
import importlib
import traceback

SEED_DIR = os.environ.get('SEED_DIR') or r'c:\odoo-dev\odoo19\migration\seed'
if SEED_DIR not in sys.path:
    sys.path.insert(0, SEED_DIR)

import seed_common  # noqa: E402

SECTIONS = [
    's10_partners',
    's20_products',
    's30_crm_sale',
    's40_purchase_stock',
    's50_accounting',
    's52_thai_finance',
    's60_hr',
    's70_project_helpdesk',
    's80_iso',
    's90_internal',
    's95_misc',
]

_only = os.environ.get('SEED_ONLY')
if _only:
    SECTIONS = [s.strip() for s in _only.split(',') if s.strip()]

ctx = seed_common.Ctx(env)
print("=== เริ่มสร้างข้อมูลตัวอย่าง Odoo 19 (บริษัท: %s) ===" % env.company.name)

for _name in SECTIONS:
    try:
        _mod = importlib.import_module(_name)
        _mod.run(ctx)
        if not seed_common.DRY_RUN:
            env.cr.commit()
    except Exception:
        env.cr.rollback()
        ctx.fail('section/%s' % _name, 'ดู traceback ด้านล่าง')
        traceback.print_exc()

if not seed_common.DRY_RUN:
    env.cr.commit()

print("=== SEED SUMMARY ===")
print(ctx.summary())
for _e in ctx.errors[:100]:
    print("ERR|%s" % _e)
print("SEED_DONE")

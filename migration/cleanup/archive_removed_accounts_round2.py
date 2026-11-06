# -*- coding: utf-8 -*-
"""Archive บัญชี OD15 (รหัส 6 หลัก) ชุดที่ 2 — placeholder เปล่า ไม่มีการอ้างอิง (odoo19_puat)

ที่มา: หลัง COA Cleanup ชุดแรก (archive_removed_accounts.py — 13 ตัว)
       และ remap 2 ชุด (remap_accounts.py 21 ตัว / remap_accounts_round2.py 8 ตัว)
       ยังเหลือบัญชี 6 หลักที่ active อยู่ 11 ตัวในระบบ
       → 4 ตัว "ไม่มีการอ้างอิง config ใด ๆ และไม่มีธุรกรรม" -> สคริปต์นี้ (Archive)
       → 6 ตัวถูกอ้างโดย journal / company / tax -> ต้อง remap ก่อนถึง archive ได้ (แยกงาน)

บัญชีที่ archive ในสคริปต์นี้ (ตรวจล่าสุด 2026-11-05):
    111002  Bank Suspense Account  asset_current   (ไม่มีอ้างอิง, 0 move line)
    111204  Outstanding Receipts   asset_current   (ไม่มีอ้างอิง, 0 move line)
    111205  Outstanding Payments   asset_current   (ไม่มีอ้างอิง, 0 move line)
    112200  Other Receivables      asset_current   (ไม่มีอ้างอิง, 0 move line)

บัญชีที่ "ไม่แตะ" ในสคริปต์นี้ (มีอ้างอิงจริง ต้อง remap ก่อน):
    111200 Bank Deposits        -> ir.default (ค่าตั้งต้นผิดพลาด)
    111201 Bank Suspense        -> suspense_account_id ของ 14 สมุดรายวัน + company
    111202 Liquidity Transfer   -> res.company.transfer_account_id, reconcile model
    111203 Bank                 -> account.journal.default_account_id (J6)
    111206 Cash(เงินสดย่อย)     -> account.journal.default_account_id (J4110)
    213200 Output VAT           -> account.tax.repartition.line.account_id x8
    999999 Current Year Earnings-> บัญชีมาตรฐาน Odoo (ห้ามแตะ)

หลักการ:
    * ทำงานผ่าน ORM เท่านั้น (ไม่ใช้ SQL ตรงสำหรับการเขียน)
    * ค่าเริ่มต้นเป็น DRY-RUN (อ่านอย่างเดียว) — ต้องตั้ง OD19_ARCHIVE_CONFIRM=1 จึงเขียนจริง
    * ตั้งสถานะ Archive (active=False) ไม่ลบ record จริง — ย้อนกลับได้ ปลอดภัยกับ FK/ประวัติ
    * รันซ้ำได้อย่างปลอดภัย (idempotent): บัญชีที่ archive แล้วจะข้าม

วิธีใช้ (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    # 1) ดูผลที่จะเกิดขึ้น (ไม่เขียนจริง)
    Get-Content -Raw migration\\cleanup\\archive_removed_accounts_round2.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http

    # 2) เขียนจริง (ต้องยืนยัน)
    $env:OD19_ARCHIVE_CONFIRM = "1"
    Get-Content -Raw migration\\cleanup\\archive_removed_accounts_round2.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
    Remove-Item Env:\\OD19_ARCHIVE_CONFIRM

ตัวแปรสภาพแวดล้อม:
    OD19_ARCHIVE_CONFIRM=1   ยืนยันการเขียนจริง (ถ้าไม่ตั้ง = DRY-RUN)
"""
import os

CONFIRM = os.environ.get('OD19_ARCHIVE_CONFIRM', '') == '1'
DRY_RUN = not CONFIRM

# ---------------------------------------------------------------------------
# บัญชี 6 หลักที่ไม่มี constraint / ไม่มีการอ้างอิง — "เอาออก" ด้วยการ Archive
# ---------------------------------------------------------------------------
REMOVE_CODES = [
    "111002",
    "111204",
    "111205",
    "112200",
]


def log(msg):
    print("ARCHIVE2| %s" % msg, flush=True)


def account_by_code(env, code, active_test=True):
    """ค้นบัญชีตามรหัส (ค่าเริ่มต้นรวมบัญชีที่ archive แล้ว)."""
    Acct = env['account.account'].sudo().with_context(active_test=active_test)
    return Acct.search([('code', '=', code)], limit=1)


def main():
    env = globals()['env']  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell
    dbname = env.cr.dbname
    log("ฐานข้อมูล: %s | โหมด: %s" % (
        dbname, "DRY-RUN (อ่านอย่างเดียว)" if DRY_RUN else "WRITE (เขียนจริง)"))

    # --- 1) หาบัญชีเป้าหมาย + รายงานสถานะปัจจุบัน -----------------------------
    to_archive = []      # (code, id) ที่ยัง active
    already = []         # (code, id) ที่ archive อยู่แล้ว
    missing = []         # code ที่ไม่พบ
    for code in REMOVE_CODES:
        acct = account_by_code(env, code, active_test=False)
        if not acct:
            missing.append(code)
            continue
        if acct.active:
            to_archive.append((code, acct.id))
        else:
            already.append((code, acct.id))

    log("พบ %d/%d บัญชี | ต้อง archive %d | archive แล้ว %d | ไม่พบ %d" % (
        len(REMOVE_CODES) - len(missing), len(REMOVE_CODES),
        len(to_archive), len(already), len(missing)))
    for code, aid in sorted(to_archive):
        log("  จะ archive: %s (id=%d)" % (code, aid))
    for code, aid in sorted(already):
        log("  archive แล้ว: %s (id=%d) — ข้าม" % (code, aid))
    for code in missing:
        log("  !! ไม่พบ: %s — ข้าม" % code)

    if DRY_RUN:
        log("DRY-RUN เสร็จ — ยังไม่แก้ข้อมูล (ตั้ง OD19_ARCHIVE_CONFIRM=1 เพื่อเขียนจริง)")
        return

    # --- 2) Archive จริง -----------------------------------------------------
    archived = 0
    for code, aid in sorted(to_archive):
        acct = env['account.account'].sudo().browse(aid).exists()
        if not acct:
            continue
        try:
            with env.cr.savepoint():
                acct.write({'active': False})
            archived += 1
            log("archive สำเร็จ %s (id=%d)" % (code, aid))
        except Exception as exc:
            lines = str(exc).strip().splitlines()
            log("!! archive ไม่สำเร็จ %s: %s" % (code, (lines[0] if lines else exc)[:180]))
    env.cr.commit()
    log("archive สำเร็จ %d/%d" % (archived, len(to_archive)))

    # --- 3) ตรวจสอบหลังทำ ----------------------------------------------------
    left = []
    for code in REMOVE_CODES:
        acct = account_by_code(env, code, active_test=False)
        if acct and acct.active:
            left.append(code)
    log("หลัง archive — บัญชียัง active คงเหลือ: %s" % (", ".join(left) if left else "—"))
    log("เสร็จสิ้น (CONFIRM=1)")


main()

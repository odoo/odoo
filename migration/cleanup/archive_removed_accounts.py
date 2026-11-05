# -*- coding: utf-8 -*-
"""Archive บัญชี OD15 (รหัส 6 หลัก) ที่ "เอาออกได้" — COA Cleanup (odoo19_puat)

ที่มา: ผลตรวจ "เอาออกได้ไหม" ของ 21 บัญชี
       → 13 ตัวไม่มี constraint (ลบได้)  -> สคริปต์นี้ (Archive)
       →  8 ตัวติด constraint (ต้อง remap) -> migration/cleanup/remap_accounts_round2.py

หลักการ:
    * ทำงานผ่าน ORM เท่านั้น (ไม่ใช้ SQL ตรงสำหรับการเขียน)
    * ค่าเริ่มต้นเป็น DRY-RUN (อ่านอย่างเดียว) — ต้องตั้ง OD19_ARCHIVE_CONFIRM=1 จึงเขียนจริง
    * ตั้งสถานะ Archive (active=False) ไม่ลบ record จริง — ย้อนกลับได้ ปลอดภัยกับ FK/ประวัติ
    * รันซ้ำได้อย่างปลอดภัย (idempotent): บัญชีที่ archive แล้วจะข้าม

วิธีใช้ (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    # 1) ดูผลที่จะเกิดขึ้น (ไม่เขียนจริง)
    Get-Content -Raw migration\\cleanup\\archive_removed_accounts.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http

    # 2) เขียนจริง (ต้องยืนยัน)
    $env:OD19_ARCHIVE_CONFIRM = "1"
    Get-Content -Raw migration\\cleanup\\archive_removed_accounts.py |
        venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
    Remove-Item Env:\\OD19_ARCHIVE_CONFIRM

ตัวแปรสภาพแวดล้อม:
    OD19_ARCHIVE_CONFIRM=1   ยืนยันการเขียนจริง (ถ้าไม่ตั้ง = DRY-RUN)
"""
import os

CONFIRM = os.environ.get('OD19_ARCHIVE_CONFIRM', '') == '1'
DRY_RUN = not CONFIRM

# ---------------------------------------------------------------------------
# บัญชีเดิม (รหัส 6 หลัก) ที่ไม่มี constraint — "เอาออก" ด้วยการ Archive
# ---------------------------------------------------------------------------
REMOVE_CODES = [
    "421100", "421200", "421400",
    "511300",
    "411200", "411300",
    "221100",
    "213300", "213303", "213100",
    "115200", "115100",
    "1140.03",
]


def log(msg):
    print("ARCHIVE| %s" % msg, flush=True)


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

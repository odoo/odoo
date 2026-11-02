# -*- coding: utf-8 -*-
"""s01_reference — นำเข้าข้อมูลอ้างอิง: ผังบัญชีจากระบบเดิม (Odoo 15 -> Odoo 19)

งานหลักของขั้นตอนนี้คือสร้าง/ปรับ "ผังบัญชี" ตามนโยบายที่ยืนยันแล้ว
(ใช้ผังบัญชีของ Odoo 15 แทนผังมาตรฐานของ Odoo 19) โดยอ่านจากไฟล์
migration/mapping/od15_chart_to_od19.csv ซึ่งเป็นไฟล์ mapping มาตรฐาน

กติกาสำคัญของ Odoo 19 (บังคับ — ถ้าฝ่าฝืนจะได้ ValidationError ทันที):
    * รหัสบัญชีต้องเข้า ^[A-Za-z0-9.]+$ (ห้ามขีดกลาง '-')
        addons/account/models/account_account.py:15  (ACCOUNT_CODE_REGEX)
        addons/account/models/account_account.py:310 (_check_account_code)
    * รหัสต้องไม่ซ้ำกันภายในบริษัท/บริษัทในเครือ (_ensure_code_is_unique:1098)

การแปลงรหัส (ตามข้อ 1 ในชีต 06_Questions ของ R02):
    แทน '-' ด้วย '.'   เช่น  1130-01 -> 1130.01 , 4110-01-01 -> 4110.01.01
    ตรวจแล้วว่าการแปลงนี้ไม่ทำให้รหัสชนกันเลยจากผัง 317 บัญชี

การรันซ้ำ (idempotent): ทุกบัญชีผูก External ID
    __import15__.account_account.<รหัส OD15 เดิม>
จึงรันซ้ำได้อย่างปลอดภัยโดยไม่เกิดบัญชีซ้ำ

การแก้ไขเพิ่มเติมตามที่ยืนยันใน Confirmation Packet รอบ R04:
    * บัญชี 4200-00, 4300-01, 4300-04 เดิมถูกตั้งเป็น Is Account Control
      (หัวข้อบัญชี) แต่ไม่มีบัญชีลูก จึงเสนอ "เอา Is Account Control ออก"
      ให้เป็น leaf และผูก EBITDA Tag ได้ครบ 8 ตัว
      (Odoo 19 ไม่มีแนวคิด Is Account Control — ทุกบัญชีลงรายการได้)
    * บัญชี 5320-01..07 กำหนด account_type = expense_depreciation มาในไฟล์ mapping แล้ว
    * ผูก EBITDA Tag รวม 94 บัญชี (Working Capital / CAPEX / Financial Debt /
      Interest Income / Interest Expense / Taxes / Exceptional Income / Exceptional Expense)
"""
import common

# ไฟล์ mapping มาตรฐานของผังบัญชี (คอลัมน์แรก = od15_code)
CHART_FILE = 'od15_chart_to_od19.csv'

# 8 EBITDA Tag หลักที่ KPI ของรายงานอ้างถึงแบบ literal — ห้ามแปล/เปลี่ยนชื่อ
# (ปกติโมดูล OCA account_ebitda_report เป็นผู้สร้าง; ที่นี่สร้างสำรองถ้ายังไม่มี)
CORE_TAGS = (
    'EBITDA / Working Capital',
    'EBITDA / CAPEX (Fixed Asset Additions)',
    'EBITDA / Financial Debt',
    'EBITDA / Interest Income',
    'EBITDA / Interest Expense',
    'EBITDA / Taxes',
    'EBITDA / Exceptional Income (Below EBITDA)',
    'EBITDA / Exceptional Expense (Below EBITDA)',
)


def run(stats):
    env = common.odoo_env()
    _sync_chart(env, stats)


def od19_code(od15_code):
    """แปลงรหัสบัญชีจากระบบเดิมให้ผ่านกติกาของ Odoo 19 ('-' -> '.')."""
    return (od15_code or '').strip().replace('-', '.')


def _ensure_tags(env):
    """ทำให้แน่ใจว่า EBITDA Tag ทั้ง 8 มีอยู่ในระบบ (สร้างเฉพาะตัวที่ยังไม่มี)

    ปกติโมดูล OCA account_ebitda_report จะสร้าง tag เหล่านี้ให้อยู่แล้ว
    ฟังก์ชันนี้ทำหน้าที่เป็นตาข่ายรองรับกรณียังไม่ได้ติดตั้งโมดูลหรือ tag ถูกลบไป
    โดยตรวจชื่อก่อนสร้างเสมอ เพื่อไม่ให้ชนข้อจำกัด unique(name, applicability, country_id)
    """
    Tag = env['account.account.tag']
    created = []
    for name in CORE_TAGS:
        if Tag.search_count([('name', '=', name), ('applicability', '=', 'accounts')]):
            continue
        _rec, action = common.upsert(
            'account.account.tag', name, {'name': name, 'applicability': 'accounts'})
        if action == 'created':
            created.append(name)
    if created:
        common.log("สร้าง EBITDA Tag เพิ่ม %d รายการ: %s" % (len(created), ', '.join(created)))


def _sync_chart(env, stats):
    rows = common.load_map(CHART_FILE)
    if not rows:
        common.log("คำเตือน: ไม่พบข้อมูลใน %s" % CHART_FILE)
        return

    Account = env['account.account'].with_context(active_test=False)
    imd = env['ir.model.data']
    company = env.company
    _ensure_tags(env)
    tag_by_name = {t.name: t.id for t in env['account.account.tag'].search([])}

    conflicts = []       # รหัสที่ชนกับบัญชีเดิมของ Odoo 19
    missing_tags = set()  # ชื่อ EBITDA Tag ที่ไม่พบในระบบใหม่

    for od15_code, row in rows.items():
        new_code = od19_code(od15_code)
        name = (row.get('name') or '').strip()
        acc_type = (row.get('od19_account_type') or '').strip()

        if not (new_code and name and acc_type):
            common.log("ผิดพลาด: ข้อมูลไม่ครบสำหรับรหัสเดิม '%s' "
                       "(code=%s name=%s type=%s)" % (od15_code, new_code, name, acc_type))
            stats.error += 1
            continue

        # กันรหัสชนกับบัญชีที่มีอยู่เดิมซึ่งไม่ได้มาจากการนำเข้า
        # (เช่น 999999 'Current Year Earnings' ของ Odoo ที่ต้องคงไว้)
        xmlid = common.get_xmlid('account.account', od15_code)
        owned_id = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
        existing = Account.search([('code', '=', new_code)], limit=1)
        if existing and existing.id != owned_id:
            conflicts.append((od15_code, new_code, existing.display_name))
            stats.skipped += 1
            continue

        vals = {
            'code': new_code,
            'name': name,
            'account_type': acc_type,
            'company_ids': [(6, 0, [company.id])],
        }
        # บัญชีลูกหนี้/เจ้าหนี้ต้องเปิดการกระทบยอด (reconcile) สำหรับจับคู่ชำระ
        # (ไม่ตั้งค่า False ให้บัญชีอื่น เพื่อไม่ทับค่า default ของ Odoo)
        if acc_type in ('asset_receivable', 'liability_payable'):
            vals['reconcile'] = True
        tag_name = (row.get('ebitda_tag_core') or '').strip()
        tag_id = tag_by_name.get(tag_name) if tag_name else None
        if tag_name and tag_id is None:
            missing_tags.add(tag_name)
        elif tag_id:
            vals['tag_ids'] = [(6, 0, [tag_id])]

        rec, action = common.upsert('account.account', od15_code, vals)
        stats.bump(action)
        # upsert ไม่เขียน x2many ให้ record ที่มีอยู่แล้ว -> ผูก tag ให้ชัดเจนที่นี่
        if rec is not None and tag_id and set(rec.tag_ids.ids) != {tag_id}:
            rec.write({'tag_ids': [(6, 0, [tag_id])]})

    common.log("ผังบัญชี: ตรวจ %d บัญชี (created=%d updated=%d skipped=%d error=%d)"
               % (len(rows), stats.created, stats.updated, stats.skipped, stats.error))

    if conflicts:
        common.log("รหัสที่ชนกับบัญชีเดิมใน Odoo 19 (%d รายการ) — คงบัญชีเดิมไว้:"
                   % len(conflicts))
        for od15_code, new_code, existing in conflicts:
            common.log("   - OD15 %s -> %s ชนกับ '%s'" % (od15_code, new_code, existing))
    if missing_tags:
        common.log("คำเตือน: ไม่พบ EBITDA Tag ต่อไปนี้: %s"
                   % ', '.join(sorted(missing_tags)))

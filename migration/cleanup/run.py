# -*- coding: utf-8 -*-
"""ล้างข้อมูลทดสอบ (seed) ออกจากฐานข้อมูล Odoo 19 ก่อนทำ ETL

หลักการ:
    * ลบ record ที่มี External ID ของชุด seed (__seed19__) และชุดนำเข้าเดิม
      (__import15__) รวมถึง "ผลพลอยได้" ของข้อมูล seed ที่ไม่มี External ID
      ของตัวเอง (ดูรายการใน SWEEP_MODELS) จึงไม่แตะข้อมูลจากโมดูลมาตรฐาน/OCA
    * เก็บไว้: ผู้ใช้ (login/รหัสผ่าน), กลุ่มสิทธิ์, บริษัท, สกุลเงิน, ผังบัญชี,
      ภาษี, สมุดรายวัน, เงื่อนไขชำระ, โมดูลที่ติดตั้ง และโครงสร้าง ir.* ทั้งหมด
    * ทำงานผ่าน ORM เท่านั้น (ไม่ใช้ SQL ตรง) และรันซ้ำได้อย่างปลอดภัย

วิธีใช้ (รันจาก root ของโปรเจกต์ c:\\odoo-dev\\odoo19):

    # 1) ดูรายการที่จะลบ (ไม่ลบจริง)
    $env:CLEAN_DRY_RUN = "1"
    venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_pdev --no-http < migration\\cleanup\\run.py
    Remove-Item Env:\\CLEAN_DRY_RUN

    # 2) ลบจริง (ต้องยืนยันด้วย CLEAN_CONFIRM=1)
    $env:CLEAN_CONFIRM = "1"
    venv19\\Scripts\\python.exe odoo-bin shell -c odoo.conf -d odoo19_pdev --no-http < migration\\cleanup\\run.py
    Remove-Item Env:\\CLEAN_CONFIRM

ตัวแปรสภาพแวดล้อม:
    CLEAN_DRY_RUN=1   แสดงรายการที่จะลบ โดยไม่ลบจริง
    CLEAN_CONFIRM=1   ยืนยันการลบจริง (ถ้าไม่ตั้ง จะหยุดและไม่ลบ)
    CLEAN_MODULES     รายชื่อโมดูล External ID ที่จะลบ (ค่าเริ่มต้น "__seed19__,__import15__")
    CLEAN_MAX_PASSES  จำนวนรอบสูงสุดของการลบซ้ำ (ค่าเริ่มต้น 15)
"""
import os

MODULES = [m.strip() for m in
           (os.environ.get('CLEAN_MODULES') or '__seed19__,__import15__').split(',')
           if m.strip()]
DRY_RUN = os.environ.get('CLEAN_DRY_RUN', '') == '1'
CONFIRM = os.environ.get('CLEAN_CONFIRM', '') == '1'
MAX_PASSES = int(os.environ.get('CLEAN_MAX_PASSES') or 15)
# เฟสที่รัน: all = ทั้งหมด, sweep = ลบผลพลอยได้อย่างเดียว, seed = ลบ record ตาม External ID อย่างเดียว
PHASE = (os.environ.get('CLEAN_PHASE') or 'all').strip().lower()

# โมเดลที่ห้ามลบเด็ดขาด (โครงสร้าง / สิทธิ์ / บริษัท / ผังบัญชี / ภาษี)
PROTECTED_MODELS = {
    'res.users', 'res.company', 'res.currency', 'res.lang', 'res.groups',
    'ir.model', 'ir.model.fields', 'ir.model.data', 'ir.module.module',
    'ir.ui.menu', 'ir.ui.view', 'ir.ui.window', 'ir.rule', 'ir.config_parameter',
    'ir.cron', 'ir.sequence', 'ir.actions.act_window', 'ir.actions.act_url',
    'account.account', 'account.journal', 'account.tax', 'res.partner.category',
}

# โมเดลธุรกรรมที่เป็น "ผลพลอยได้" ของข้อมูล seed (ไม่มี External ID ของตัวเอง)
# เช่น ใบรับ/ใบจ่ายสินค้า, การเคลื่อนไหวสต็อก, log การใช้รถ, สัญญาขายที่ระบบสร้างให้
# ต้องลบก่อน record แม่ (partner/vehicle/product/order/project) จึงจะลบได้
# ลำดับในลิสต์ = ลำดับที่พยายามลบ (ลูกก่อนพ่อ) และวนซ้ำหลายรอบจนไม่เหลือ
SWEEP_MODELS = [
    'fleet.vehicle.assignation.log',
    'fleet.vehicle.odometer',
    'fleet.vehicle.cost',
    'maintenance.request',
    'stock.move.line',
    'stock.move',
    'stock.picking',
    'stock.lot',
    'stock.quant',
    'od19.sales.contract',
    # ตารางของโมดูล custom ที่อ้างอิงคู่ค้า/แผนก
    'od19.service.card',
    'od19.warranty.claim',
    'od19.iso.customer.satisfaction',
    'od19.iso.supplier.evaluation',
    'od19.iso.audit',
    # เอกสารซื้อ/ขาย + การเงิน
    'purchase.order.line',
    'purchase.order',
    'sale.order.line',
    'sale.order',
    'account.payment',
    'account.move',
    # ใบเบิกค่าใช้จ่าย (อ้างอิงพนักงาน/สินค้า)
    'hr.expense',
    # โครงการ (สินค้า/พนักงาน/แผนกของระบบไม่ลบ — record ของ seed ถูกลบด้วย External ID แล้ว)
    'project.task',
    'project.project',
    # รถ (ลบหลังเอกสารที่อ้างถึง)
    'fleet.vehicle',
    'fleet.vehicle.model',
    # คู่ค้าทดสอบ (ยกเว้นคู่ค้าของบริษัท/ผู้ใช้ที่ถูกป้องกันไว้ใน _sweep_models)
    'res.partner',
]


def log(msg):
    print("CLEAN| %s" % msg, flush=True)


def _protected_partner_ids(env):
    """คู่ค้าที่ต้องคงไว้: คู่ค้าของบริษัท และของทุกผู้ใช้ (ผูกกับ login)."""
    ids = set()
    ids.add(env.company.partner_id.id)
    ids.update(env['res.users'].sudo().with_context(active_test=False).search([])
               .mapped('partner_id').ids)
    return {i for i in ids if i}


def _collect(env):
    """คืนค่า (by_model, rows) ของ ir.model.data ที่มี module ตรงกับ MODULES."""
    rows = env['ir.model.data'].sudo().search_read(
        [('module', 'in', MODULES)], ['model', 'res_id', 'name'])
    by_model = {}
    for r in rows:
        by_model.setdefault(r['model'], set()).add(r['res_id'])
    return by_model, rows


def _prepare_unlink(rec, model):
    """ปรับสถานะเอกสารให้ลบได้ก่อน (Odoo ห้ามลบเอกสารที่ยังไม่ draft/ยกเลิก).

    คืนค่า None ถ้าปกติ หรือข้อความ error ถ้าปรับสถานะไม่สำเร็จ
    """
    try:
        if model == 'account.move' and rec.state != 'draft':
            rec.button_draft()
        elif model == 'sale.order' and rec.state not in ('draft', 'cancel'):
            rec.action_cancel()
        elif model == 'purchase.order' and rec.state != 'cancel':
            # Odoo 19 บังคับให้ purchase.order ต้องอยู่สถานะ cancel เท่านั้นจึงจะลบได้
            # (draft ลบไม่ได้ ต่างจาก sale.order ที่ลบได้ทั้ง draft และ cancel)
            rec.button_cancel()
        elif model == 'account.payment' and rec.state != 'draft':
            rec.action_draft()
        elif model == 'hr.expense' and rec.state != 'draft':
            # Odoo ห้ามลบใบเบิกที่ approved/posted — ต้องกลับเป็น draft ก่อน
            if hasattr(rec, 'action_reset_expense_to_draft'):
                rec.action_reset_expense_to_draft()
            else:
                rec.write({'state': 'draft'})
    except Exception as exc:
        lines = str(exc).strip().splitlines()
        return (lines[0] if lines else exc.__class__.__name__)[:220]
    return None


def _sweep_models(env, errors, protected_partners=None):
    """ลบข้อมูลธุรกรรมผลพลอยได้ทั้งหมด (ทำซ้ำจนไม่เหลือ) — คืนจำนวนที่ลบได้."""
    total = 0
    for attempt in range(1, MAX_PASSES + 1):
        removed = 0
        for model in SWEEP_MODELS:
            if model not in env:
                continue
            recs = env[model].sudo().search([])
            if model == 'res.partner' and protected_partners:
                # ห้ามลบคู่ค้าของบริษัท/ผู้ใช้ (ผูกกับ login)
                recs = recs - env['res.partner'].sudo().browse(list(protected_partners))
            for rec in recs:
                try:
                    with env.cr.savepoint():
                        _prepare_unlink(rec, model)
                        rec.unlink()
                    removed += 1
                except Exception as exc:
                    if model not in errors:
                        lines = str(exc).strip().splitlines()
                        errors[model] = (lines[0] if lines else exc.__class__.__name__)[:220]
        if removed:
            env.cr.commit()
            total += removed
            log("SWEEP รอบที่ %d: ลบผลพลอยได้ %d รายการ" % (attempt, removed))
        else:
            break
    log("SWEEP รวม %d รายการ" % total)
    return total


def _unlink_records(env, model, ids, protected_partners, errors):
    """ลบ record ทีละตัวพร้อม savepoint (คืนค่า done, failed)."""
    try:
        Model = env[model].sudo()
    except KeyError:
        log("  ข้าม (ไม่มีโมเดลในรีจิสทรี): %s (%d)" % (model, len(ids)))
        return 0, 0

    recs = Model.browse(list(ids)).exists()
    if model == 'res.partner' and protected_partners:
        recs = recs - Model.browse(list(protected_partners))
    if not recs:
        return 0, 0

    done = failed = 0
    for rec in recs:
        prep_err = None
        try:
            with env.cr.savepoint():
                prep_err = _prepare_unlink(rec, model)
                rec.unlink()
            done += 1
        except Exception as exc:
            failed += 1
            if model not in errors:
                if prep_err:
                    errors[model] = prep_err
                else:
                    lines = str(exc).strip().splitlines()
                    errors[model] = (lines[0] if lines else exc.__class__.__name__)[:220]
    return done, failed


def main():
    env = globals()['env']  # noqa: F821 — ตัวแปร env มีให้โดย odoo shell

    log("โมดูลที่ล้าง: %s | DRY_RUN=%s | CONFIRM=%s" % (', '.join(MODULES), DRY_RUN, CONFIRM))

    by_model, rows = _collect(env)
    total = sum(len(v) for v in by_model.values())
    log("พบ record ที่ผูก External ID รวม %d รายการ ใน %d โมเดล" % (total, len(by_model)))

    if DRY_RUN:
        for model, ids in sorted(by_model.items(), key=lambda x: -len(x[1])):
            mark = " [PROTECTED]" if model in PROTECTED_MODELS else ""
            log("  %-42s %4d%s" % (model, len(ids), mark))
        log("DRY-RUN — ยังไม่ลบข้อมูลจริง (ตั้ง CLEAN_CONFIRM=1 เพื่อลบจริง)")
        return

    if not CONFIRM:
        log("ยังไม่ได้รับยืนยัน — หยุด (ตั้ง CLEAN_CONFIRM=1 เพื่อลบจริง)")
        return

    protected_partners = _protected_partner_ids(env)
    log("คู่ค้าที่จะคงไว้ (บริษัท/ผู้ใช้): %d ราย" % len(protected_partners))

    errors = {}
    # ลบผลพลอยได้ก่อน (stock move/picking, log รถ, สัญญาที่ระบบสร้าง) เพื่อปลดล็อก record แม่
    if PHASE in ('all', 'sweep'):
        _sweep_models(env, errors, protected_partners)

    if PHASE == 'sweep':
        log("โหมด sweep — จบการทำงาน")
        for model, msg in sorted(errors.items()):
            log("    ติด: %-38s → %s" % (model, msg))
        return

    pending = {m: set(i) for m, i in by_model.items()}
    grand_done = 0

    for attempt in range(1, MAX_PASSES + 1):
        removed_any = False
        stuck_this_pass = {}
        for model in sorted(pending):
            ids = pending[model]
            if not ids:
                continue
            done, failed = _unlink_records(env, model, ids, protected_partners, errors)
            if done:
                env.cr.commit()
                grand_done += done
                removed_any = True
            if failed:
                stuck_this_pass[model] = failed
            else:
                # ลบครบแล้ว (หรือไม่มี record จริง) — เอา model นี้ออกจากคิว
                pending[model] = set()
        pending = {m: i for m, i in pending.items() if i}
        log("รอบที่ %d: ลบสะสม %d รายการ | ค้าง %d โมเดล" % (attempt, grand_done, len(pending)))
        for model, n in sorted(stuck_this_pass.items(), key=lambda x: -x[1]):
            log("    ค้าง: %-38s %3d → %s" % (model, n, errors.get(model, '-')))
        if not pending or not removed_any:
            break

    if pending:
        log("สรุป: ยังลบไม่ได้ %d โมเดล" % len(pending))
        for model, ids in sorted(pending.items(), key=lambda x: -len(x[1])):
            log("    %-42s %4d" % (model, len(ids)))

    # ล้าง External ID ของโมดูลที่ลบแล้ว (เหลือเฉพาะที่ชี้ไปยัง record ที่คงไว้)
    imd = env['ir.model.data'].sudo()
    left = imd.search([('module', 'in', MODULES)])
    removed_ids = 0
    for rec in left:
        target = env[rec.model].browse(rec.res_id).exists() if rec.model in env else None
        if target is not None and target:
            continue
        try:
            with env.cr.savepoint():
                rec.unlink()
                removed_ids += 1
        except Exception:
            pass
    env.cr.commit()

    log("ลบ record สำเร็จรวม %d รายการ | External ID ที่ล้าง %d" % (grand_done, removed_ids))
    log("เสร็จสิ้น (DRY_RUN=%s, CONFIRM=%s)" % (DRY_RUN, CONFIRM))


main()

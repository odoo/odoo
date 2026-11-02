# -*- coding: utf-8 -*-
"""s08_opening — ยอดยกมา: AR/AP, บัญชีงบดุล, สินค้าคงเหลือ, สินทรัพย์, WHT/เบิกล่วงหน้า/เช็ค

ข้อควรระวังที่สุดของขั้นตอนนี้:
    ยอดยกมาคือ "จุดตั้งต้น" ของบัญชีจริง ต้องกระทบยอดกับงบการเงินของระบบเดิม
    ให้ตรงก่อนนำเข้า (AR/AP/สินค้าคงเหลือ/สินทรัพย์) ห้ามรันจริงโดยไม่ตรวจยอด

การออกแบบ (ยืนยันแล้ว):
    * วันตัดยอด = 2026-10-31 (OPENING_DATE)
    * นำเข้า "เฉพาะบัญชีงบดุล" (ไม่ยกบัญชีกำไรขาดทุน) เพราะยอดยกมาคือจุดตั้งต้น
      ของรอบบัญชีใหม่ ส่วนกำไรขาดทุนสะสมของปีปัจจุบันแสดงผ่านบัญชีคู่ปรับ
    * บัญชีคู่ปรับ (offset) = 999999 Current Year Earnings (account_type='equity_unaffected')
    * สมุดรายวันของยอดยกมา = BRF 'Bring Forward'
    * ทุกบรรทัดของ AR/AP ต้องมี partner_id เพื่อให้รายงานอายุลูกหนี้/เจ้าหนี้ทำงาน
      และ AR/AP แยกเป็น "1 ใบต่อคู่ค้า" (idempotent ผ่าน External ID ต่อคู่ค้า)

การรันซ้ำ (idempotent):
    account.move ไม่สามารถใช้ common.upsert ได้ (เพราะต้องประกอบ line_ids เอง)
    จึงใช้ _upsert_move() ซึ่งผูก External ID __import15__.account_move.<key>
    ถ้าใบนั้น post แล้วจะข้ามทันทีเมื่อรันซ้ำ
"""
import common
import legacy

# วันตัดยอดยอดยกมา (opening date)
OPENING_DATE = '2026-10-31'

# สมุดรายวันยอดยกมา
OPENING_JOURNAL_CODE = 'BRF'

# บัญชีประเภทกำไรขาดทุน (จะไม่ยกมา)
PROFIT_LOSS_TYPES = (
    'income', 'income_other',
    'expense', 'expense_direct_cost', 'expense_depreciation',
)

# บัญชีคุมลูกหนี้/เจ้าหนี้ (ต้องแยกต่อคู่ค้าเพื่อให้ aging ทำงาน)
RECEIVABLE_PAYABLE_TYPES = ('asset_receivable', 'liability_payable')


def run(stats):
    env = common.odoo_env()
    _opening_ar_ap(env, stats)
    _opening_gl(env, stats)
    _opening_stock(env, stats)
    _opening_assets(env, stats)
    _opening_wht_advance_cheque(env, stats)


# --------------------------------------------------------------------------
# ตัวช่วยพื้นฐาน: อ้างอิงบัญชี/คู่ค้า/สมุดรายวัน ของ Odoo 19
# --------------------------------------------------------------------------
def _account(env, od15_code):
    """คืนค่า account.account ของ Odoo 19 ที่ได้จากรหัสบัญชีเดิม (ผ่าน External ID)."""
    xmlid = common.get_xmlid('account.account', od15_code)
    acc_id = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if not acc_id:
        return None
    return env['account.account'].browse(acc_id)


def _partner(env, legacy_id):
    """คืนค่า res.partner ของ Odoo 19 ที่ได้จาก id เดิม (ผ่าน External ID)."""
    xmlid = common.get_xmlid('res.partner', legacy_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if not pid:
        return None
    return env['res.partner'].browse(pid)


def _journal(env, code):
    """คืนค่าสมุดรายวันตามรหัส (จำกัดเฉพาะบริษัทปัจจุบัน)."""
    return env['account.journal'].search(
        [('code', '=', code), ('company_id', '=', env.company.id)], limit=1)


def _offset_account(env):
    """บัญชีคู่ปรับยอดยกมา = 999999 Current Year Earnings (equity_unaffected)."""
    acc = env['account.account'].search(
        [('account_type', '=', 'equity_unaffected')], limit=1)
    if not acc:
        raise ValueError("ไม่พบบัญชีคู่ปรับ 'Current Year Earnings' (equity_unaffected) "
                         "ในบริษัท %s" % env.company.display_name)
    return acc


def _upsert_move(env, key, move_vals):
    """สร้าง/ตรวจ account.move พร้อม line_ids โดยผูก External ID (idempotent).

    ถ้าใบเดิม post แล้วจะข้าม (คืน 'skipped') เพื่อไม่ให้ยอดยกมาถูกแก้ซ้ำ
    ถ้าใบเดิมยังเป็น draft จะเขียนบรรทัดใหม่แล้ว post ให้
    """
    xmlid = common.get_xmlid('account.move', key)
    lines = move_vals.get('line_ids') or []
    if common.DRY_RUN:
        common.log('[DRY-RUN] จะสร้าง account.move %s (%d บรรทัด)"%s"'
                   % (xmlid, len(lines), move_vals.get('ref', '')))
        return None, 'skipped'

    imd = env['ir.model.data']
    Move = env['account.move']
    existing_id = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if existing_id:
        rec = Move.browse(existing_id)
        if rec.state == 'posted':
            return rec, 'skipped'
        rec.write({'line_ids': [(5, 0, 0)] + lines})
        rec.action_post()
        return rec, 'updated'

    rec = Move.create(move_vals)
    rec.action_post()
    imd._update_xmlids(
        [{'xml_id': xmlid, 'record': rec, 'noupdate': True}], update=True)
    return rec, 'created'


def _line_vals(account, amount, partner=None, name='ยอดยกมา'):
    """สร้างค่าบรรทัด journal entry จากยอดคงเหลือ (เดบิตเป็นบวก)."""
    amount = round(amount, 2)
    vals = {
        'account_id': account.id,
        'name': name,
        'debit': amount if amount > 0 else 0.0,
        'credit': -amount if amount < 0 else 0.0,
    }
    if partner is not None:
        vals['partner_id'] = partner.id
    return vals


def _fetch_trial_balance(date):
    """ยอดคงเหลือต่อบัญชี ณ วันตัดยอด (เฉพาะที่มียอดไม่เป็นศูนย์)."""
    sql = (
        "SELECT a.code AS account_code, "
        "       round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s "
        "GROUP BY a.code "
        "HAVING round(sum(l.balance)::numeric, 2) <> 0 "
        "ORDER BY a.code"
    )
    return legacy.fetch_all(sql, {'date': date})


# --------------------------------------------------------------------------
# (a) ยอดยกมาลูกหนี้/เจ้าหนี้ (AR/AP) — 1 ใบต่อคู่ค้า
# --------------------------------------------------------------------------
def _fetch_arap(date):
    """ยอดคงเหลือลูกหนี้/เจ้าหนี้ต่อ (บัญชี, คู่ค้า) ณ วันตัดยอด."""
    sql = (
        "SELECT a.code AS account_code, l.partner_id AS partner_id, "
        "       round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s "
        "GROUP BY a.code, l.partner_id "
        "HAVING round(sum(l.balance)::numeric, 2) <> 0 "
        "ORDER BY a.code"
    )
    return legacy.fetch_all(sql, {'date': date})


def _opening_ar_ap(env, stats):
    """สร้าง Opening JE แยกลูกหนี้/เจ้าหนี้เป็นรายคู่ค้า."""
    journal = _journal(env, OPENING_JOURNAL_CODE)
    if not journal:
        raise ValueError("ไม่พบสมุดรายวัน '%s' สำหรับยอดยกมา" % OPENING_JOURNAL_CODE)
    offset = _offset_account(env)

    # เลือกเฉพาะบรรทัดที่เป็นบัญชีคุมลูกหนี้/เจ้าหนี้ของ Odoo 19
    grouped = {}      # partner_id -> list of line vals
    no_partner = []
    unknown = 0
    for row in _fetch_arap(OPENING_DATE):
        acc = _account(env, row['account_code'])
        if not acc:
            common.log("คำเตือน: ไม่พบบัญชี OD19 สำหรับรหัสเดิม %s" % row['account_code'])
            unknown += 1
            continue
        if acc.account_type not in RECEIVABLE_PAYABLE_TYPES:
            continue
        partner_id = row['partner_id']
        if partner_id is None:
            no_partner.append((acc, float(row['balance'])))
        else:
            grouped.setdefault(partner_id, []).append((acc, float(row['balance'])))

    if unknown:
        stats.error += unknown

    total = 0.0
    for partner_id, items in grouped.items():
        partner = _partner(env, partner_id)
        if not partner:
            common.log("คำเตือน: ไม่พบคู่ค้า OD19 สำหรับ id เดิม %s" % partner_id)
            stats.error += 1
            continue
        lines = [_line_vals(acc, bal, partner=partner) for acc, bal in items]
        net = round(sum(bal for _acc, bal in items), 2)
        lines.append(_line_vals(offset, -net))
        _rec, action = _upsert_move(env, 'arap.%s' % partner_id, {
            'move_type': 'entry',
            'date': OPENING_DATE,
            'journal_id': journal.id,
            'ref': 'ยอดยกมาลูกหนี้/เจ้าหนี้ - %s' % partner.display_name,
            'line_ids': [(0, 0, vals) for vals in lines],
        })
        stats.bump(action)
        total += net

    # บรรทัดที่ไม่มีคู่ค้า (เช่น ค่าเผื่อหนี้สงสัยจะสูญ, ค่าใช้จ่ายค้างจ่ายรวม)
    if no_partner:
        lines = [_line_vals(acc, bal) for acc, bal in no_partner]
        net = round(sum(bal for _acc, bal in no_partner), 2)
        lines.append(_line_vals(offset, -net))
        _rec, action = _upsert_move(env, 'arap.nopartner', {
            'move_type': 'entry',
            'date': OPENING_DATE,
            'journal_id': journal.id,
            'ref': 'ยอดยกมาลูกหนี้/เจ้าหนี้ (ไม่ระบุคู่ค้า)',
            'line_ids': [(0, 0, vals) for vals in lines],
        })
        stats.bump(action)
        total += net

    common.log("AR/AP ยกมา: %d คู่ค้า + 1 ใบไม่ระบุคู่ค้า | ยอดสุทธิ=%.2f"
               % (len(grouped), total))


# --------------------------------------------------------------------------
# (b) ยอดยกมาบัญชีงบดุลอื่น ๆ (ยกเว้น AR/AP ที่ทำไปแล้ว)
# --------------------------------------------------------------------------
def _opening_gl(env, stats):
    """สร้าง Opening JE รวมสำหรับบัญชีงบดุลที่เหลือ (คู่กับบัญชีคู่ปรับ)."""
    journal = _journal(env, OPENING_JOURNAL_CODE)
    if not journal:
        raise ValueError("ไม่พบสมุดรายวัน '%s' สำหรับยอดยกมา" % OPENING_JOURNAL_CODE)
    offset = _offset_account(env)

    lines = []
    net = 0.0
    unknown = []
    for row in _fetch_trial_balance(OPENING_DATE):
        acc = _account(env, row['account_code'])
        if not acc:
            unknown.append(row['account_code'])
            continue
        if acc.account_type in PROFIT_LOSS_TYPES:
            continue  # ไม่ยกบัญชีกำไรขาดทุน (สะท้อนผ่านบัญชีคู่ปรับ)
        if acc.account_type in RECEIVABLE_PAYABLE_TYPES:
            continue  # จัดการแล้วใน _opening_ar_ap
        bal = float(row['balance'])
        lines.append(_line_vals(acc, bal))
        net += bal

    if unknown:
        common.log("คำเตือน: ไม่พบบัญชี OD19 %d รหัส: %s"
                   % (len(unknown), ', '.join(sorted(unknown))))
        stats.error += len(unknown)

    if not lines:
        common.log("GL ยกมา: ไม่มีบัญชีที่ต้องยก")
        return

    net = round(net, 2)
    lines.append(_line_vals(offset, -net))
    _rec, action = _upsert_move(env, 'opening.gl', {
        'move_type': 'entry',
        'date': OPENING_DATE,
        'journal_id': journal.id,
        'ref': 'ยอดยกมาบัญชีงบดุลจากระบบเดิม (Odoo 15)',
        'line_ids': [(0, 0, vals) for vals in lines],
    })
    stats.bump(action)
    common.log("GL ยกมา: %d บัญชี | ยอดสุทธิ=%.2f | คู่ปรับ(Current Year Earnings)=%.2f"
               % (len(lines) - 1, net, -net))


# --------------------------------------------------------------------------
# (c) ยอดยกมาสินค้าคงเหลือ
# --------------------------------------------------------------------------
# บัญชีสินค้าคงเหลือในผังบัญชีเดิม (ใช้เป็นยอดอ้างอิงจาก GL)
STOCK_GL_CODE = '1140-01'


def _od15_balance(code, date):
    """ยอดคงเหลือของบัญชีเดียวในระบบเดิม ณ วันตัดยอด."""
    sql = (
        "SELECT round(sum(l.balance)::numeric, 2) AS balance "
        "FROM account_move_line l "
        "JOIN account_move m ON m.id = l.move_id "
        "JOIN account_account a ON a.id = l.account_id "
        "WHERE m.state = 'posted' AND m.date <= %(date)s AND a.code = %(code)s"
    )
    rows = legacy.fetch_all(sql, {'date': date, 'code': code})
    if rows and rows[0]['balance'] is not None:
        return float(rows[0]['balance'])
    return 0.0


def _fetch_internal_quants():
    """ปริมาณคงเหลือในคลังภายใน (ทุก internal location) สรุปต่อสินค้า (variant)."""
    sql = (
        "SELECT q.product_id AS variant_id, sum(q.quantity)::numeric AS qty "
        "FROM stock_quant q "
        "JOIN stock_location l ON l.id = q.location_id "
        "WHERE l.usage = 'internal' "
        "GROUP BY q.product_id "
        "HAVING sum(q.quantity) <> 0"
    )
    return legacy.fetch_all(sql)


def _fetch_cost_by_variant():
    """ต้นทุนสินค้า (standard_price) ต่อ variant จาก ir_property ของระบบเดิม."""
    sql = (
        "SELECT split_part(ip.res_id, ',', 2)::int AS variant_id, ip.value_float AS cost "
        "FROM ir_property ip JOIN ir_model_fields f ON f.id = ip.fields_id "
        "WHERE f.model = 'product.product' AND f.name = 'standard_price' "
        "  AND ip.res_id LIKE 'product.product,%' AND ip.value_float IS NOT NULL"
    )
    return {r['variant_id']: float(r['cost']) for r in legacy.fetch_all(sql)}


def _variant_template_map():
    """แผนที่ variant_id -> product template id ของระบบเดิม."""
    rows = legacy.fetch_all(
        "SELECT id AS variant_id, product_tmpl_id AS tmpl_id FROM product_product")
    return {r['variant_id']: r['tmpl_id'] for r in rows}


def _od19_product(env, tmpl_id):
    """คืน product.product ของ Odoo 19 ที่ได้จาก template id เดิม (ผ่าน External ID)."""
    if not tmpl_id:
        return None
    xmlid = common.get_xmlid('product.template', tmpl_id)
    pid = env['ir.model.data']._xmlid_to_res_id(xmlid, raise_if_not_found=False)
    if not pid:
        return None
    return env['product.template'].browse(pid).product_variant_id or None


def _opening_stock(env, stats):
    """(c) ยอดยกมาสินค้าคงเหลือ.

    แนวทางที่เลือก (อนุมัติแล้ว): "ยึดยอด GL 24.82M"
      * ปริมาณคงเหลือยึดตาม stock_quant ของระบบเดิม (ทุก internal location)
        แล้วรวบเข้าคลังหลัก (WH/Stock) ของ Odoo 19
      * ปรับต้นทุน (standard_price) ของแต่ละสินค้าตามสัดส่วน ให้ผลรวมมูลค่า
        เท่ากับยอดคงเหลือของบัญชีสินค้าคงเหลือใน GL (1140-01)
      * ปรับยอดผ่าน stock.quant + _apply_inventory(date=วันตัดยอด)
        (Odoo 19 ยกเลิกโมเดล stock.inventory แล้ว เหลือเฉพาะ wizard)
    หมายเหตุ: บริษัทตั้งค่าประเมินสินค้าคงคลังเป็น 'periodic' จึงไม่เกิดรายการบัญชี
      จากการปรับสต็อก (ยอดใน GL มาจาก Opening JE ใน _opening_gl แล้ว)
      ถ้าเปลี่ยนเป็น perpetual ภายหลังต้องตรวจการบัญชีซ้ำ (double count) ทันที
    """
    warehouse = env['stock.warehouse'].search(
        [('company_id', '=', env.company.id)], limit=1)
    if not warehouse:
        raise ValueError("ไม่พบคลังสินค้า (stock.warehouse) ของบริษัท %s"
                         % env.company.display_name)
    stock_loc = warehouse.lot_stock_id

    target_total = _od15_balance(STOCK_GL_CODE, OPENING_DATE)
    if target_total <= 0:
        common.log("สต็อกยกมา: ยอด GL บัญชี %s = 0 — ข้าม" % STOCK_GL_CODE)
        stats.skipped += 1
        return

    costs = _fetch_cost_by_variant()
    vtmpl = _variant_template_map()

    items = []           # [product, qty, ต้นทุนเดิม, ต้นทุนใหม่]
    missing = 0
    current_total = 0.0
    for row in _fetch_internal_quants():
        prod = _od19_product(env, vtmpl.get(row['variant_id']))
        if not prod:
            missing += 1
            continue
        qty = float(row['qty'] or 0.0)
        cost = costs.get(row['variant_id'], 0.0) or 0.0
        items.append([prod, qty, cost, cost])
        current_total += cost * qty

    if missing:
        # สินค้าที่มีสต็อกแต่ไม่พบใน Odoo 19 = สินค้าที่ถูก archive ในระบบเดิม
        # (s04 นำเข้าเฉพาะ active=true) จึงอยู่นอกขอบเขตการนำเข้า — ยอดตามต้นทุนยัง
        # ถูกปรับให้ครบยอด GL ผ่านสัดส่วนอยู่แล้ว จึงไม่นับเป็น error
        common.log("หมายเหตุ: สินค้าที่มีสต็อกแต่ไม่นำเข้า (archive ในระบบเดิม) = %d รายการ"
                   % missing)
        stats.skipped += missing
    if not items or current_total <= 0:
        common.log("สต็อกยกมา: ไม่พบต้นทุนสินค้าในระบบเดิม — ข้าม")
        stats.skipped += 1
        return

    if common.DRY_RUN:
        common.log("[DRY-RUN] สต็อกยกมา: %d สินค้า | มูลค่าตามต้นทุนเดิม=%.2f | "
                   "เป้าหมาย GL(%s)=%.2f"
                   % (len(items), current_total, STOCK_GL_CODE, target_total))
        stats.skipped += 1
        return

    # ปรับต้นทุนตามสัดส่วนให้ผลรวมเท่ากับยอด GL (คำนวณใหม่ทุกครั้ง -> รันซ้ำได้)
    factor = target_total / current_total
    new_total = 0.0
    for it in items:
        it[3] = round(it[2] * factor, 2)
        new_total += it[3] * it[1]

    # กลืนเศษจากการปัดเศษที่รายการมูลค่าสูงสุด เพื่อให้ผลรวมตรงกับยอด GL
    residual = round(target_total - new_total, 2)
    if abs(residual) >= 0.01:
        idx = max(range(len(items)), key=lambda i: abs(items[i][1] * items[i][3]))
        if abs(items[idx][1]) > 1e-6:
            items[idx][3] = round(items[idx][3] + residual / items[idx][1], 2)

    for prod, _qty, _old_cost, new_cost in items:
        if abs((prod.standard_price or 0.0) - new_cost) > 1e-9:
            prod.with_company(env.company).standard_price = new_cost

    # --- ปรับยอดคงเหลือ (quant) ที่คลังหลัก แล้ว apply inventory ณ วันตัดยอด ---
    inv_loc = env['stock.location'].search(
        [('usage', '=', 'inventory'),
         ('company_id', 'in', [False, env.company.id])], limit=1)
    if inv_loc and not env['ir.default'].with_company(env.company)._get_model_defaults(
            'product.template').get('property_stock_inventory'):
        env['ir.default'].set('product.template', 'property_stock_inventory',
                              inv_loc.id, company_id=env.company.id)

    qty_by_product = {it[0].id: it[1] for it in items}
    Quant = env['stock.quant']
    quants = Quant.search([
        ('product_id', 'in', list(qty_by_product)),
        ('location_id', '=', stock_loc.id),
        ('company_id', '=', env.company.id)])
    existing_pids = set(quants.mapped('product_id').ids)
    to_create = [{'product_id': pid,
                  'location_id': stock_loc.id,
                  'company_id': env.company.id}
                 for pid in qty_by_product if pid not in existing_pids]
    if to_create:
        quants |= Quant.with_context(inventory_mode=True).create(to_create)

    # ปรับเฉพาะรายการที่ยอดปัจจุบันยังไม่ตรง (รันซ้ำจะไม่มีรายการ -> ไม่เกิด move เปล่า)
    to_apply = quants.filtered(
        lambda q: abs((q.quantity or 0.0)
                      - qty_by_product.get(q.product_id.id, 0.0)) > 1e-6)
    for q in to_apply:
        q.with_context(inventory_mode=True).write(
            {'inventory_quantity': qty_by_product.get(q.product_id.id, 0.0)})
    if to_apply:
        to_apply._apply_inventory(date=OPENING_DATE)
        stats.updated += len(to_apply)

    final_total = sum(it[3] * it[1] for it in items)
    common.log("สต็อกยกมา: %d สินค้า | จำนวนรวม=%.2f | มูลค่าต้นทุนใหม่=%.2f | "
               "GL(%s)=%.2f | ผลต่าง=%.2f"
               % (len(items), sum(it[1] for it in items), final_total,
                  STOCK_GL_CODE, target_total, target_total - final_total))


# --------------------------------------------------------------------------
# (d) ยอดยกมาสินทรัพย์ถาวร
# --------------------------------------------------------------------------
# สถานะสินทรัพย์เดิม -> สถานะของ OCA account.asset
ASSET_STATE_MAP = {'draft': 'draft', 'open': 'open', 'close': 'close'}
# รอบการคิดค่าเสื่อม (เดือนของระบบเดิม) -> ตัวเลือกรอบของ OCA
ASSET_METHOD_PERIOD = {1: 'month', 3: 'quarter', 12: 'year'}
# วิธีคิดเวลา ('eom' เป็นค่าที่ระบบเดิมกำหนดเอง) -> ตัวเลือกของ OCA
ASSET_METHOD_TIME = {'year': 'year', 'number': 'number', 'eom': 'year', 'end': 'year'}


def _purge_asset_seed(env, stats):
    """ล้างข้อมูลตัวอย่าง (seed) ของ account.asset / account.asset.profile ก่อนนำเข้า.

    หมายเหตุ: OCA กันการลบสินทรัพย์ที่ไม่ใช่สถานะ draft ไว้ (ondelete guard)
    จึงต้องลบด้วย context _force_unlink=True ซึ่งเป็นวิธียกเว้น guard ที่ Odoo
    รองรับ (MODULE_UNINSTALL_FLAG) — ข้อมูล seed ชุดนี้ไม่มีรายการบัญชีผูกอยู่
    ลำดับต้องลบ "สินทรัพย์" ให้หมดก่อน "แผนผัง" เพื่อไม่ให้ติด FK
    """
    imd = env['ir.model.data']

    def imported_ids(model):
        return set(imd.search(
            [('model', '=', model), ('module', '=', common.MODULE_PREFIX)]
        ).mapped('res_id'))

    Asset = env['account.asset'].with_context(
        active_test=False, _force_unlink=True)
    seed_assets = Asset.search([('id', 'not in', list(imported_ids('account.asset')))])
    removed = 0
    if seed_assets:
        try:
            seed_assets.unlink()
            removed = len(seed_assets)
        except Exception as exc:
            raise ValueError("ล้างข้อมูลตัวอย่างสินทรัพย์ไม่สำเร็จ: %s" % exc)

    Profile = env['account.asset.profile'].with_context(
        active_test=False, _force_unlink=True)
    seed_profiles = Profile.search(
        [('id', 'not in', list(imported_ids('account.asset.profile')))])
    removed_prof = 0
    if seed_profiles:
        try:
            seed_profiles.unlink()
            removed_prof = len(seed_profiles)
        except Exception as exc:
            raise ValueError("ล้างแผนผังสินทรัพย์ตัวอย่างไม่สำเร็จ: %s" % exc)

    if removed or removed_prof:
        common.log("ล้างข้อมูลตัวอย่างสินทรัพย์: %d รายการ + แผนผัง %d รายการ"
                   % (removed, removed_prof))


def _fetch_asset_categories():
    """หมวดหมู่สินทรัพย์เดิม พร้อมรหัสบัญชี/สมุดรายวันที่เกี่ยวข้อง."""
    sql = (
        "SELECT c.id, c.name, c.method, c.method_number, c.method_period, c.method_time, "
        "       aa.code AS asset_code, ad.code AS depr_code, "
        "       ae.code AS exp_code, j.code AS journal_code "
        "FROM account_asset_category c "
        "LEFT JOIN account_account aa ON aa.id = c.account_asset_id "
        "LEFT JOIN account_account ad ON ad.id = c.account_depreciation_id "
        "LEFT JOIN account_account ae ON ae.id = c.account_depreciation_expense_id "
        "LEFT JOIN account_journal j ON j.id = c.journal_id "
        "ORDER BY c.id"
    )
    return legacy.fetch_all(sql)


def _fetch_assets():
    """ทะเบียนสินทรัพย์เดิมทั้งหมด (ทุกสถานะ) พร้อมค่าเสื่อมสะสม ณ วันตัดยอด.

    ค่าเสื่อมสะสม = accumulated_depreciation_bf + ผลรวมบรรทัดค่าเสื่อมที่ลงบัญชีแล้ว
    และมีวันที่ไม่เกินวันตัดยอด
    """
    sql = (
        "SELECT a.id, a.name, a.code, a.category_id, a.state, a.date, a.value, "
        "       COALESCE(a.accumulated_depreciation_bf, 0) + COALESCE(("
        "           SELECT sum(d.amount) FROM account_asset_depreciation_line d "
        "           WHERE d.asset_id = a.id AND d.move_check "
        "             AND d.depreciation_date <= %(date)s), 0) AS acc_dep "
        "FROM account_asset_asset a "
        "ORDER BY a.id"
    )
    return legacy.fetch_all(sql, {'date': OPENING_DATE})


def _sync_asset_profiles(env, stats):
    """สร้าง account.asset.profile จากหมวดหมู่สินทรัพย์เดิม."""
    profiles = {}
    for cat in _fetch_asset_categories():
        asset_acc = _account(env, cat['asset_code'])
        depr_acc = _account(env, cat['depr_code'])
        exp_acc = _account(env, cat['exp_code'])
        journal = _journal(env, cat['journal_code'] or '')
        if not (asset_acc and depr_acc and exp_acc and journal):
            common.log("คำเตือน: หมวดหมู่สินทรัพย์เดิม '%s' (id=%s) จับคู่บัญชี/สมุดรายวัน "
                       "ไม่ครบ — ข้าม" % (cat['name'], cat['id']))
            stats.error += 1
            continue
        try:
            period = ASSET_METHOD_PERIOD.get(int(cat['method_period'] or 0), 'month')
        except (TypeError, ValueError):
            period = 'month'
        vals = {
            'name': (cat['name'] or '').strip() or ('Category %s' % cat['id']),
            'account_asset_id': asset_acc.id,
            'account_depreciation_id': depr_acc.id,
            'account_expense_depreciation_id': exp_acc.id,
            'journal_id': journal.id,
            'method': cat['method'] or 'linear',
            'method_number': int(cat['method_number'] or 5),
            'method_period': period,
            'method_time': ASSET_METHOD_TIME.get(cat['method_time'] or 'year', 'year'),
            'prorata': True,
            'company_id': env.company.id,
        }
        rec, action = common.upsert('account.asset.profile', cat['id'], vals)
        stats.bump(action)
        profiles[cat['id']] = rec
    return profiles


def _upsert_asset_dep_line(env, asset, amount):
    """สร้าง/ปรับบรรทัดค่าเสื่อมยกมา (init_entry) ให้ค่าเสื่อมสะสมตรงกับระบบเดิม.

    บรรทัด init_entry ไม่สร้างรายการบัญชี จึงไม่กระทบ GL ที่ยกมาแล้ว
    แต่ทำให้ value_residual ของสินทรัพย์ตรงกับมูลค่าสุทธิของระบบเดิม
    """
    amount = round(amount or 0.0, 2)
    Line = env['account.asset.line']
    lines = asset.depreciation_line_ids.filtered(
        lambda line: line.type == 'depreciate' and line.init_entry)
    if amount <= 0:
        if lines:
            lines.unlink()
        return
    if lines:
        if abs((lines[0].amount or 0.0) - amount) > 1e-6:
            lines[0].with_context(allow_asset_line_update=True).write(
                {'amount': amount})
    else:
        Line.create({
            'asset_id': asset.id,
            'name': 'ยกมา',
            'amount': amount,
            'line_date': OPENING_DATE,
            'init_entry': True,
            'type': 'depreciate',
        })


def _opening_assets(env, stats):
    """(d) ยอดยกมาสินทรัพย์ถาวร — นำเข้าทั้งทะเบียน (ทุกสถานะ).

    ใช้โมเดล account.asset (OCA account_asset_management)
    ยอดสินทรัพย์/ค่าเสื่อมสะสมใน GL มาจาก Opening JE แล้ว (บรรทัด init_entry
    ไม่กระทบ GL) — ที่นี่เพียงสร้างทะเบียนให้ตรงกับระบบเดิมเพื่อให้ค่าเสื่อม
    งวดถัดไปคำนวณต่อได้ถูกต้อง
    """
    if common.DRY_RUN:
        rows = _fetch_assets()
        total = sum(float(r['value'] or 0.0) for r in rows)
        nbv = sum(float(r['value'] or 0.0) - float(r['acc_dep'] or 0.0) for r in rows)
        common.log("[DRY-RUN] สินทรัพย์ยกมา: %d รายการ | มูลค่าทะเบียน=%.2f | "
                   "มูลค่าสุทธิ=%.2f" % (len(rows), total, nbv))
        stats.skipped += 1
        return

    _purge_asset_seed(env, stats)
    profiles = _sync_asset_profiles(env, stats)

    rows = _fetch_assets()
    total = 0.0
    nbv_total = 0.0
    for row in rows:
        profile = profiles.get(row['category_id'])
        if not profile:
            common.log("คำเตือน: ไม่พบแผนผังสินทรัพย์สำหรับหมวดหมู่เดิม id=%s "
                       "(สินทรัพย์ id=%s)" % (row['category_id'], row['id']))
            stats.error += 1
            continue
        value = float(row['value'] or 0.0)
        acc_dep = float(row['acc_dep'] or 0.0)
        vals = {
            'name': (row['name'] or '').strip() or ('Asset %s' % row['id']),
            'code': (row['code'] or '').strip()[:32] or False,
            'purchase_value': value,
            'salvage_value': 0.0,
            'date_start': row['date'],
            'profile_id': profile.id,
            'company_id': env.company.id,
            'state': ASSET_STATE_MAP.get(row['state'], 'draft'),
        }
        try:
            rec, action = common.upsert('account.asset', row['id'], vals)
            stats.bump(action)
        except Exception as exc:
            common.log("ผิดพลาด: นำเข้าสินทรัพย์ id=%s ('%s') ไม่ได้: %s"
                       % (row['id'], row['name'], exc))
            stats.error += 1
            continue
        _upsert_asset_dep_line(env, rec, acc_dep)
        total += value
        nbv_total += value - acc_dep

    common.log("สินทรัพย์ยกมา: %d รายการ | มูลค่าทะเบียน=%.2f | มูลค่าสุทธิ=%.2f"
               % (len(rows), total, nbv_total))


# --------------------------------------------------------------------------
# (e) WHT ค้าง / เงินเบิกล่วงหน้า / เช็คค้าง — ทะเบียนย่อย (ไม่ลง GL)
# --------------------------------------------------------------------------
# ยอดคงค้างของทั้งสามประเภทเป็นยอดในบัญชีงบดุล (ภาษีหัก ณ ที่จ่ายค้างจ่าย,
# เงินจ่ายล่วงหน้าผู้ขาย, เช็ครับล่วงหน้า) ซึ่งถูกยกผ่าน _opening_gl() แล้ว
# การนำเข้าส่วนนี้จึงสร้างเฉพาะ "ทะเบียน" (state='draft') เพื่อค้นประวัติ/อ้างอิง
# โดยจงใจไม่เรียก action_post / action_confirm / action_to_pay / action_done
# เพราะเมธอดเหล่านั้นสร้างและ post account.move เอง ซึ่งจะบันทึกซ้ำกับ GL
# ที่ยกมาแล้ว (double counting)

# ประเภทรายได้ของระบบเดิม (tax_condition) -> wht_cert_income_type ของ Odoo 19
# (ชุดค่าตรงกันทั้งสองระบบ)
WHT_CERT_INCOME_TYPES = (
    '1', '2', '3', '4A',
    '4B11', '4B12', '4B13', '4B14',
    '4B21', '4B22', '4B23', '4B24', '4B25',
    '5', '6',
)
# แบบฟอร์มภาษีของระบบเดิม (tax_type) -> income_tax_form ของ Odoo 19
WHT_INCOME_TAX_FORM = {'1': 'pnd1', '2': 'pnd2', '3': 'pnd3', '53': 'pnd53'}


def _od19_currency(env, code):
    """คืนค่า res.currency จากรหัสสกุลเงิน (เช่น THB) — ค่าเริ่มต้นคือสกุลของบริษัท."""
    if not code:
        return env.company.currency_id
    currency = env['res.currency'].with_context(active_test=False).search(
        [('name', '=', code)], limit=1)
    return currency or env.company.currency_id


def _opening_wht_advance_cheque(env, stats):
    """(e) นำเข้าทะเบียนย่อย: เช็ค / ภาษีหัก ณ ที่จ่าย / เงินจ่ายล่วงหน้า.

    ทั้งสามส่วน "ไม่ลง GL" — สร้างเป็นเอกสารสถานะ draft เท่านั้น
    (ยอดคงค้างถูกยกผ่าน Opening JE ใน _opening_gl เรียบร้อยแล้ว)
    """
    _opening_cheques(env, stats)
    _opening_wht(env, stats)
    _opening_advances(env, stats)


# --- (e.1) ทะเบียนเช็ค -----------------------------------------------------
def _fetch_cheques():
    """ทะเบียนเช็คเดิม (cheque_date ใช้วันที่เช็ค ถ้าว่างใช้วันที่สร้าง)."""
    sql = (
        "SELECT c.id, c.name, c.amount, c.state, "
        "       COALESCE(c.date, c.create_date::date) AS cheque_date, "
        "       c.clear_date, c.pay_to, c.memo, c.ac_payee, c.partner_id, "
        "       c.bank_branch, c.bank_id AS bank_legacy_id, rb.name AS bank_name, "
        "       j.code AS journal_code, cur.name AS currency_code "
        "FROM dtr_cheque c "
        "LEFT JOIN account_journal j ON j.id = c.journal_id "
        "LEFT JOIN res_bank rb ON rb.id = c.bank_id "
        "LEFT JOIN res_currency cur ON cur.id = c.currency_id "
        "ORDER BY c.id"
    )
    return legacy.fetch_all(sql)


def _opening_cheques(env, stats):
    """นำเข้า dtr_cheque -> account.cheque (state='draft', ไม่กระทบ GL).

    ระบบเดิมบันทึกเฉพาะ "เช็ครับล่วงหน้าจากลูกหนี้" (account_payment.payment_type
    = 'inbound' ทุกรายการ) จึงกำหนด cheque_type='customer' ทั้งหมด
    """
    rows = _fetch_cheques()
    if common.DRY_RUN:
        total = sum(float(r['amount'] or 0.0) for r in rows)
        common.log("[DRY-RUN] เช็คยกมา: %d รายการ | ยอดรวม=%.2f (state='draft', ไม่ลง GL)"
                   % (len(rows), total))
        stats.skipped += len(rows)
        return

    bank_cache = {}
    imported = 0
    for row in rows:
        partner = _partner(env, row['partner_id'])
        if not partner:
            common.log("คำเตือน: ไม่พบคู่ค้าสำหรับเช็คเดิม id=%s — ข้าม" % row['id'])
            stats.error += 1
            continue
        vals = {
            'name': row['name'],
            # เช็คจากระบบเดิมเป็นเช็ครับจากลูกหนี้ทั้งหมด
            'cheque_type': 'customer',
            'partner_id': partner.id,
            'amount': float(row['amount'] or 0.0),
            'currency_id': _od19_currency(env, row['currency_code']).id,
            'cheque_date': row['cheque_date'],
            'due_date': row['cheque_date'],
            'clear_date': row['clear_date'] or False,
            'pay_to': row['pay_to'] or False,
            'memo': row['memo'] or False,
            'ac_payee': bool(row['ac_payee']),
            'bank_branch': row['bank_branch'] or False,
            'state': 'draft',
        }
        journal = _journal(env, row['journal_code'] or '')
        if journal:
            vals['journal_id'] = journal.id
        else:
            common.log("คำเตือน: ไม่พบสมุดรายวัน '%s' ของเช็คเดิม id=%s"
                       % (row['journal_code'], row['id']))
        legacy_bank_id = row['bank_legacy_id']
        if legacy_bank_id:
            if legacy_bank_id not in bank_cache:
                bank_cache[legacy_bank_id] = common.upsert(
                    'res.bank', legacy_bank_id,
                    {'name': (row['bank_name'] or '').strip() or 'Bank %s' % legacy_bank_id})[0]
            bank = bank_cache[legacy_bank_id]
            if bank:
                vals['bank_id'] = bank.id
        _rec, action = common.upsert('account.cheque', row['id'], vals)
        if action != 'skipped':
            imported += 1
        stats.bump(action)

    common.log("เช็คยกมา: นำเข้า %d รายการ | ธนาคารใหม่ %d รายการ"
               % (imported, len(bank_cache)))


# --- (e.2) ทะเบียนภาษีหัก ณ ที่จ่าย ----------------------------------------
def _fetch_wht():
    """ใบรับรองหัก ณ ที่จ่ายเดิม (สูงสุด 3 ประเภทเงินได้ต่อใบ)."""
    sql = (
        "SELECT w.id, w.name, w.name_seq, w.pay_date, w.partner_id, w.state, "
        "       w.tax_type, w.tax_condition, w.tax_condition2, w.tax_condition3, "
        "       w.pay_amount1, w.wht_amount1, "
        "       w.pay_amount2, w.wht_amount2, "
        "       w.pay_amount3, w.wht_amount3, "
        "       cur.name AS currency_code "
        "FROM dtr_wht w "
        "LEFT JOIN res_currency cur ON cur.id = w.currency_id "
        "ORDER BY w.id"
    )
    return legacy.fetch_all(sql)


def _opening_wht(env, stats):
    """นำเข้า dtr_wht -> withholding.tax.cert (state='draft', ไม่กระทบ GL)."""
    rows = _fetch_wht()
    if common.DRY_RUN:
        total = sum(float(r['wht_amount1'] or 0.0)
                    + float(r['wht_amount2'] or 0.0)
                    + float(r['wht_amount3'] or 0.0) for r in rows)
        common.log("[DRY-RUN] ใบรับรองหัก ณ ที่จ่ายยกมา: %d รายการ | ยอดหักรวม=%.2f "
                   "(state='draft', ไม่ลง GL)" % (len(rows), total))
        stats.skipped += len(rows)
        return

    selections = dict(
        env['withholding.tax.cert.line']._fields['wht_cert_income_type'].selection)
    for row in rows:
        form = WHT_INCOME_TAX_FORM.get(str(row['tax_type'] or ''))
        if not form:
            common.log("คำเตือน: ไม่รู้จักแบบฟอร์มภาษี tax_type='%s' (WHT เดิม id=%s)"
                       % (row['tax_type'], row['id']))
            stats.error += 1
            continue
        partner = _partner(env, row['partner_id'])
        if not partner:
            common.log("คำเตือน: ไม่พบผู้รับเงินสำหรับ WHT เดิม id=%s — ข้าม" % row['id'])
            stats.error += 1
            continue

        lines = []
        for cond, base, amount in (
                (row['tax_condition'], row['pay_amount1'], row['wht_amount1']),
                (row['tax_condition2'], row['pay_amount2'], row['wht_amount2']),
                (row['tax_condition3'], row['pay_amount3'], row['wht_amount3'])):
            if cond not in WHT_CERT_INCOME_TYPES:
                continue
            base = round(float(base or 0.0), 2)
            amount = round(float(amount or 0.0), 2)
            if not base and not amount:
                continue
            lines.append((0, 0, {
                'wht_cert_income_type': cond,
                'wht_cert_income_desc': selections.get(cond) or False,
                'base': base,
                'amount': amount,
            }))

        number = (row['name'] or '').strip() or '/'
        vals = {
            'name': number,
            'number': number,
            'date': row['pay_date'],
            'partner_id': partner.id,
            'company_id': env.company.id,
            'company_partner_id': env.company.partner_id.id,
            'income_tax_form': form,
            'tax_payer': 'withholding',
            'state': 'draft',
            'wht_line': lines,
        }
        _rec, action = common.upsert('withholding.tax.cert', row['id'], vals)
        stats.bump(action)

    common.log("ใบรับรองหัก ณ ที่จ่ายยกมา: นำเข้า %d รายการ" % len(rows))


# --- (e.3) ทะเบียนเงินจ่ายล่วงหน้าผู้ขาย -----------------------------------
def _fetch_advances():
    """รายการจ่ายล่วงหน้าผู้ขายเดิม พร้อมยอดที่จ่ายจริง (จาก account_payment)."""
    sql = (
        "SELECT p.id, p.name, p.number, p.partner_id, p.bill_date, p.document_date, "
        "       p.notes, p.state, cur.name AS currency_code, "
        "       COALESCE((SELECT sum(pm.amount) "
        "                 FROM account_payment_dtr_account_prepayment_rel r "
        "                 JOIN account_payment pm ON pm.id = r.account_payment_id "
        "                 JOIN account_move mm ON mm.id = pm.move_id "
        "                      AND mm.state = 'posted' "
        "                 WHERE r.dtr_account_prepayment_id = p.id), 0) AS paid_amount "
        "FROM dtr_account_prepayment p "
        "LEFT JOIN res_currency cur ON cur.id = p.currency_id "
        "ORDER BY p.id"
    )
    return legacy.fetch_all(sql)


def _opening_advances(env, stats):
    """นำเข้า dtr_account_prepayment -> account.advance (state='draft', ไม่กระทบ GL).

    ระบบเดิมเป็น "การจ่ายบิลล่วงหน้าให้ผู้ขาย" ยอดที่บันทึกคือเงินที่จ่ายจริง
    (จาก account_payment) ส่วนรายการที่ยังไม่มีการจ่าย (draft/open ที่ไม่มีความ
    เคลื่อนไหว) จะถูกข้าม เพราะ account.advance บังคับให้ยอดต้องมากกว่าศูนย์
    """
    rows = _fetch_advances()
    if common.DRY_RUN:
        usable = [r for r in rows if float(r['paid_amount'] or 0.0) > 0]
        total = sum(float(r['paid_amount'] or 0.0) for r in usable)
        common.log("[DRY-RUN] เงินจ่ายล่วงหน้ายกมา: %d/%d รายการ (ที่มีการจ่ายจริง) | "
                   "ยอดรวม=%.2f (state='draft', ไม่ลง GL)"
                   % (len(usable), len(rows), total))
        stats.skipped += len(rows)
        return

    skipped = 0
    imported = 0
    for row in rows:
        amount = round(float(row['paid_amount'] or 0.0), 2)
        if amount <= 0:
            skipped += 1
            continue
        partner = _partner(env, row['partner_id'])
        if not partner:
            common.log("คำเตือน: ไม่พบผู้ขายสำหรับเงินจ่ายล่วงหน้าเดิม id=%s — ข้าม" % row['id'])
            stats.error += 1
            continue
        account = partner.with_company(env.company).property_account_payable_id
        if not account:
            common.log("คำเตือน: ไม่พบบัญชีเจ้าหนี้ของผู้ขาย '%s' (advance เดิม id=%s) — ข้าม"
                       % (partner.display_name, row['id']))
            stats.error += 1
            continue

        number = (row['number'] or '').strip()
        name = number if number and number != 'Draft' else (row['name'] or '').strip()
        vals = {
            'name': name or ('ADV/%s' % row['id']),
            'advance_type': 'supplier',
            'od19_advance_kind': 'prepayment',
            'partner_id': partner.id,
            'amount': amount,
            'currency_id': _od19_currency(env, row['currency_code']).id,
            'date': row['bill_date'] or row['document_date'],
            'advance_account_id': account.id,
            'state': 'draft',
            'note': row['notes'] or False,
        }
        _rec, action = common.upsert('account.advance', row['id'], vals)
        if action != 'skipped':
            imported += 1
        stats.bump(action)

    common.log("เงินจ่ายล่วงหน้ายกมา: นำเข้า %d รายการ | ข้าม (ไม่มียอดจ่ายจริง) %d รายการ"
               % (imported, skipped))

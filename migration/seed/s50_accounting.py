# -*- coding: utf-8 -*-
"""s50_accounting — ใบแจ้งหนี้/ใบกำกับภาษี, การชำระเงิน และภาษีหัก ณ ที่จ่าย"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def _line(prod, qty, price, tax):
    return (0, 0, {
        'product_id': prod.product_variant_id.id,
        'name': prod.name,
        'quantity': qty,
        'price_unit': price,
        'tax_ids': [(6, 0, tax.ids)] if tax else [(6, 0, [])],
    })


def _upsert_move(ctx, key, vals):
    """สร้าง/อัปเดตใบแจ้งหนี้ แต่ไม่แตะเอกสารที่ post แล้ว

    เอกสารที่ post แล้วจะแก้ไขฟิลด์อย่าง invoice_date/date ไม่ได้
    จึงคืน record เดิมโดยไม่เขียนทับ (idempotent เมื่อรันซ้ำ/รันต่างวัน)
    """
    existing = ctx.get('account.move', key)
    if existing and existing.state == 'posted':
        return existing
    return ctx.upsert('account.move', key, vals)


def run(ctx):
    ctx.step('s50_accounting', 'ใบแจ้งหนี้/ใบกำกับภาษี และการชำระเงิน')
    if not ctx.has('account.move'):
        ctx.warn('ไม่มีโมเดล account.move — ข้าม')
        return

    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    vendors = ctx.state.get('vendors') or list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))
    products = ctx.state.get('products') or list(ctx.find('product.template', [], limit=12))
    if not customers or not products:
        ctx.warn('ข้อมูลไม่พอ — ข้ามใบแจ้งหนี้')
        return

    tax_sale = ctx.find('account.tax', [('amount', '=', 7.0), ('type_tax_use', '=', 'sale')], limit=1)
    tax_purch = ctx.find('account.tax', [('amount', '=', 7.0), ('type_tax_use', '=', 'purchase')], limit=1)
    journal_sale = ctx.journal('INV')
    journal_purch = ctx.journal('BILL')

    out_invoices, in_invoices = [], []

    # ---------------- ใบแจ้งหนี้ขาย ----------------
    for i in range(10):
        partner = customers[i % len(customers)]
        p1 = products[i % len(products)]
        p2 = products[(i + 1) % len(products)]
        lines = [_line(p1, 1 + (i % 3), p1.list_price, tax_sale)]
        if i % 2 == 0:
            lines.append(_line(p2, 2, p2.list_price, tax_sale))
        vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': _d(-30 + i * 3),
            'date': _d(-30 + i * 3),
            'invoice_date_due': _d(0 + i * 3),
            'journal_id': journal_sale.id if journal_sale else False,
            'invoice_line_ids': lines,
            'ref': 'PO-CUST-%03d' % (i + 1),
        }
        rec = _upsert_move(ctx, 'out_inv_%02d' % (i + 1), vals)
        if rec:
            out_invoices.append(rec)

    # ---------------- ใบกำกับภาษีซื้อ (Vendor Bill) ----------------
    for i in range(10):
        partner = vendors[i % len(vendors)]
        p = products[(i + 3) % len(products)]
        vals = {
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': _d(-25 + i * 3),
            'date': _d(-25 + i * 3),
            'invoice_date_due': _d(5 + i * 3),
            'journal_id': journal_purch.id if journal_purch else False,
            'invoice_line_ids': [_line(p, 2 + (i % 4), p.standard_price or p.list_price, tax_purch)],
            'ref': 'INV-VEND-%03d' % (i + 1),
        }
        rec = _upsert_move(ctx, 'in_inv_%02d' % (i + 1), vals)
        if rec:
            in_invoices.append(rec)
            # ใบกำกับภาษีซื้อ: ต้องระบุเลขที่/วันที่ใบกำกับของผู้ขายก่อน Post
            tinvs = rec.tax_invoice_ids
            if tinvs and rec.state == 'draft':
                ctx.guard('tininv/%s' % rec.id, tinvs.write, {
                    'tax_invoice_number': 'VIV-%05d' % (20001 + i),
                    'tax_invoice_date': _d(-25 + i * 3)})

    ctx.state['out_invoices'] = out_invoices
    ctx.state['in_invoices'] = in_invoices
    ctx.log("ใบแจ้งหนี้ขาย %d / ใบกำกับภาษีซื้อ %d" % (len(out_invoices), len(in_invoices)))

    # ---------------- ยืนยัน (post) บางใบ ----------------
    posted = 0
    for inv in out_invoices[:4] + in_invoices[:4]:
        if inv.state == 'draft':
            res = ctx.guard('post/%s' % inv.id, inv.action_post)
            if res is not None:
                posted += 1
    ctx.log("post สำเร็จ %d ใบ" % posted)

    # ---------------- การชำระเงิน ----------------
    if ctx.has('account.payment'):
        bank = ctx.journal('BNK1') or ctx.journal('MISC')
        made = 0
        for i in range(10):
            is_customer = (i % 2 == 0)
            partner = customers[i % len(customers)] if is_customer else vendors[i % len(vendors)]
            vals = {
                'payment_type': 'inbound' if is_customer else 'outbound',
                'partner_type': 'customer' if is_customer else 'supplier',
                'partner_id': partner.id,
                'amount': 15000.0 + i * 2500,
                'date': _d(-10 + i),
                'journal_id': bank.id if bank else False,
            }
            rec = ctx.upsert('account.payment', 'pay_%02d' % (i + 1), vals)
            if rec:
                made += 1
        ctx.log("การชำระเงิน: %d" % made)

    # ---------------- ภาษีหัก ณ ที่จ่าย (WHT) ----------------
    if ctx.has('account.withholding.move') and in_invoices:
        made = 0
        for i, inv in enumerate(in_invoices[:10]):
            partner = vendors[i % len(vendors)]
            vals = {
                'move_id': inv.id,
                'partner_id': partner.id,
                'amount_income': 10000.0 + i * 1500,
                'company_id': ctx.company.id,
            }
            rec = ctx.upsert('account.withholding.move', 'wht_%02d' % (i + 1), vals)
            if rec:
                made += 1
        ctx.log("รายการภาษีหัก ณ ที่จ่าย: %d" % made)
    else:
        ctx.warn('ไม่มีโมเดล/ข้อมูลสำหรับ WHT — ข้าม')

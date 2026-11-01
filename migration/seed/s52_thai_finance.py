# -*- coding: utf-8 -*-
"""s52_thai_finance — เครื่องมือการเงินไทย: เช็ค เงินสดย่อย เงินทดรอง อากรแสตมป์
ภาษีเงินได้รอการตัดบัญชี และ e-Tax / e-WHT
"""
import seed_common
import datetime


def _d(offset=0):
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d')


def _dt(offset=0):
    return (datetime.datetime.now() + datetime.timedelta(days=offset)).strftime('%Y-%m-%d %H:%M:%S')


def run(ctx):
    ctx.step('s52_thai_finance', 'เช็ค/เงินสดย่อย/ทดรอง/อากรแสตมป์/รอตัดบัญชี/e-Tax')
    customers = ctx.state.get('customers') or list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    vendors = ctx.state.get('vendors') or list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))
    thb = ctx.thb
    cash_acc = ctx.account('111100') or ctx.account('111300') or ctx.find('account.account', [('account_type', '=', 'asset_cash')], limit=1)
    other_recv = ctx.account('112200') or ctx.account('112100') or ctx.find('account.account', [('account_type', '=', 'asset_receivable')], limit=1)
    expense_acc = ctx.find('account.account', [('account_type', '=', 'expense')], limit=1)

    # ---------------- สมุดเช็ค + เช็ค ----------------
    if ctx.has('account.cheque.book'):
        bank = ctx.journal('BNK1')
        ctx.upsert('account.cheque.book', 'book_01', {
            'first_cheque_no': '0000001', 'quantity': 50,
            'journal_id': bank.id if bank else False, 'state': 'draft'})

    if ctx.has('account.cheque'):
        made = 0
        for i in range(10):
            is_cust = (i % 2 == 0)
            partner = customers[i % len(customers)] if is_cust else vendors[i % len(vendors)]
            if not partner:
                continue
            vals = {
                'name': 'CHQ-%05d' % (10001 + i),
                'cheque_type': 'customer' if is_cust else 'supplier',
                'partner_id': partner.id,
                'amount': 25000.0 + i * 5000,
                'currency_id': thb.id if thb else False,
                'cheque_date': _d(-5 + i),
                'due_date': _d(10 + i),
                'memo': 'เช็คทดสอบ seed',
            }
            if ctx.upsert('account.cheque', 'cheque_%02d' % (i + 1), vals):
                made += 1
        ctx.log("เช็ค: %d" % made)

    # ---------------- เงินสดย่อย ----------------
    funds = []
    if ctx.has('petty.cash.fund'):
        for i, (key, name, amt) in enumerate([('fund_01', 'เงินสดย่อย สำนักงานใหญ่', 50000.0),
                                              ('fund_02', 'เงินสดย่อย โรงงาน', 30000.0)]):
            rec = ctx.upsert('petty.cash.fund', key, {
                'name': name, 'account_id': cash_acc.id if cash_acc else False,
                'amount': amt, 'currency_id': thb.id if thb else False})
            if rec:
                funds.append(rec)
        ctx.log("กองทุนเงินสดย่อย: %d" % len(funds))

        if ctx.has('petty.cash.transaction') and funds:
            made = 0
            for i in range(10):
                fund = funds[i % len(funds)]
                vals = {
                    'fund_id': fund.id,
                    'name': 'รายการเงินสดย่อย %02d' % (i + 1),
                    'amount': 500.0 + i * 250,
                    'transaction_type': 'expense' if i % 5 != 4 else 'replenishment',
                    'date': _d(-15 + i),
                    'expense_account_id': expense_acc.id if expense_acc else False,
                }
                if ctx.upsert('petty.cash.transaction', 'pct_%02d' % (i + 1), vals):
                    made += 1
            ctx.log("รายการเงินสดย่อย: %d" % made)

    # ---------------- เงินทดรองจ่าย/รับ ----------------
    if ctx.has('account.advance') and other_recv:
        made = 0
        for i in range(10):
            is_cust = (i % 2 == 0)
            partner = customers[i % len(customers)] if is_cust else vendors[i % len(vendors)]
            if not partner:
                continue
            vals = {
                'name': 'ADV-%05d' % (20001 + i),
                'advance_type': 'customer' if is_cust else 'supplier',
                'partner_id': partner.id,
                'amount': 20000.0 + i * 3000,
                'currency_id': thb.id if thb else False,
                'date': _d(-12 + i),
                'advance_account_id': other_recv.id,
            }
            if ctx.upsert('account.advance', 'adv_%02d' % (i + 1), vals):
                made += 1
        ctx.log("เงินทดรอง: %d" % made)

    # ---------------- อากรแสตมป์ ----------------
    rates = []
    if ctx.has('od19.stamp.duty.rate'):
        for i, (key, rtype, amt) in enumerate([
                ('rate_01', 'scale', 1.0), ('rate_02', 'scale', 5.0),
                ('rate_03', 'fixed', 20.0), ('rate_04', 'fixed', 50.0)]):
            rec = ctx.upsert('od19.stamp.duty.rate', key, {
                'name': 'อัตราอากร %s %s' % (rtype, amt), 'rate_type': rtype, 'rate_amount': amt})
            if rec:
                rates.append(rec)

    if ctx.has('od19.stamp.duty') and rates:
        made = 0
        for i in range(10):
            rate = rates[i % len(rates)]
            vals = {
                'name': 'SD-%05d' % (30001 + i),
                'company_id': ctx.company.id,
                'rate_id': rate.id,
                'instrument_date': _d(-20 + i),
                'amount': 100000.0 + i * 20000,
            }
            if ctx.upsert('od19.stamp.duty', 'stamp_%02d' % (i + 1), vals):
                made += 1
        ctx.log("อากรแสตมป์: %d" % made)

    # ---------------- ภาษีเงินได้รอการตัดบัญชี (TAS 12) ----------------
    ws = None
    if ctx.has('od19.deferred.tax.worksheet'):
        ws = ctx.upsert('od19.deferred.tax.worksheet', 'dt_ws_01', {
            'name': 'TAS12 งวดทดสอบ %s' % datetime.date.today().year,
            'company_id': ctx.company.id,
            'date_from': _d(-365), 'date_to': _d(0), 'state': 'draft'})
        if ws:
            cats = ['fixed_asset', 'provision', 'allowance', 'inventory', 'other']
            for i in range(10):
                ctx.upsert('od19.deferred.tax.line', 'dt_line_%02d' % (i + 1), {
                    'worksheet_id': ws.id,
                    'name': 'รายการรอตัดบัญชี %02d' % (i + 1),
                    'category': cats[i % len(cats)],
                    'carrying_amount': 500000.0 + i * 50000,
                    'tax_base': 450000.0 + i * 40000,
                })
            ctx.log("ใบงานภาษีรอการตัดบัญชี + 10 รายการ")

    # ---------------- e-Tax / e-WHT ----------------
    docs = []
    out_invoices = ctx.state.get('out_invoices') or []
    # เปิดใช้ e-Tax ที่ระดับบริษัท (จำเป็นก่อนสร้างเอกสาร e-Tax)
    if 'od19_etax_enabled' in ctx.fields('res.company'):
        ctx.guard('etax-enable', ctx.company.write, {'od19_etax_enabled': True})
    if 'od19_ewht_enabled' in ctx.fields('res.company'):
        ctx.guard('ewht-enable', ctx.company.write, {'od19_ewht_enabled': True})
    if ctx.has('od19.etax.document'):
        # e-Tax ออกได้เฉพาะเอกสารขาย (ใบแจ้งหนี้/ใบลดหนี้/ใบเสร็จ) ไม่รวมใบกำกับภาษีซื้อ
        moves = [m for m in out_invoices
                 if m.move_type in ('out_invoice', 'out_refund', 'out_receipt')]
        for i, mv in enumerate(moves[:10]):
            rec = ctx.upsert('od19.etax.document', 'etax_doc_%02d' % (i + 1), {
                'name': 'ETAX-%05d' % (40001 + i),
                'document_type': 'tax_invoice',
                'company_id': ctx.company.id,
                'move_id': mv.id,
                'issue_datetime': _dt(-15 + i),
                'state': 'draft',
            })
            if rec:
                docs.append(rec)

    if ctx.has('od19.etax.submission') and docs:
        ctx.guard('etax-submission', ctx.upsert, 'od19.etax.submission', 'etax_sub_01', {
            'name': 'การส่ง e-Tax ประจำเดือน (ทดสอบ)',
            'company_id': ctx.company.id,
            'channel': 'mock', 'state': 'draft',
            'document_ids': [(6, 0, [d.id for d in docs])],
        })
        ctx.log("e-Tax: เอกสาร %d รายการ + submission" % len(docs))

    if ctx.has('od19.ewht.submission'):
        whts = list(ctx.find('account.withholding.move', [], limit=10))
        if whts:
            ctx.guard('ewht-submission', ctx.upsert, 'od19.ewht.submission', 'ewht_sub_01', {
                'name': 'การส่ง e-WHT ประจำเดือน (ทดสอบ)',
                'company_id': ctx.company.id,
                'channel': 'mock', 'state': 'draft',
                'move_ids': [(6, 0, [w.id for w in whts])],
            })
            ctx.log("e-WHT submission: อ้างอิง %d รายการ" % len(whts))

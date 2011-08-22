# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from lxml import etree

import netsvc
from osv import osv, fields
import decimal_precision as dp
from tools.translate import _


class account_voucher(osv.osv):

    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('type', False)

    def _get_period(self, cr, uid, context=None):
        if context is None: context = {}
        if context.get('period_id', False):
            return context.get('period_id')
        if context.get('invoice_id', False):
            company_id = self.pool.get('account.invoice').browse(cr, uid, context['invoice_id'], context=context).company_id.id
            context.update({'company_id': company_id})
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        return periods and periods[0] or False

    def _get_journal(self, cr, uid, context=None):
        if context is None: context = {}
        journal_pool = self.pool.get('account.journal')
        invoice_pool = self.pool.get('account.invoice')
        if context.get('invoice_id', False):
            currency_id = invoice_pool.browse(cr, uid, context['invoice_id'], context=context).currency_id.id
            journal_id = journal_pool.search(cr, uid, [('currency', '=', currency_id)], limit=1)
            return journal_id and journal_id[0] or False
        if context.get('journal_id', False):
            return context.get('journal_id')
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            return context.get('search_default_journal_id')

        ttype = context.get('type', 'bank')
        if ttype in ('payment', 'receipt'):
            ttype = 'bank'
        res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)
        return res and res[0] or False

    def _get_tax(self, cr, uid, context=None):
        if context is None: context = {}
        journal_pool = self.pool.get('account.journal')
        journal_id = context.get('journal_id', False)
        if not journal_id:
            ttype = context.get('type', 'bank')
            res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)
            if not res:
                return False
            journal_id = res[0]

        if not journal_id:
            return False
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
            return tax_id
        return False

    def _get_currency(self, cr, uid, context=None):
        if context is None: context = {}
        journal_pool = self.pool.get('account.journal')
        journal_id = context.get('journal_id', False)
        if journal_id:
            journal = journal_pool.browse(cr, uid, journal_id, context=context)
#            currency_id = journal.company_id.currency_id.id
            if journal.currency:
                return journal.currency.id
        return False

    def _get_partner(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('partner_id', False)

    def _get_reference(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('reference', False)

    def _get_narration(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('narration', False)

    def _get_amount(self, cr, uid, context=None):
        if context is None:
            context= {}
        return context.get('amount', 0.0)

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if context is None: context = {}
        return [(r['id'], (str("%.2f" % r['amount']) or '')) for r in self.read(cr, uid, ids, ['amount'], context, load='_classic_write')]

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        if context is None: context = {}
        if not view_id and context.get('invoice_type', False):
            if context.get('invoice_type', False) in ('out_invoice', 'out_refund'):
                result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
            else:
                result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
            result = result and result[1] or False
            view_id = result
        if not view_id and view_type == 'form' and context.get('line_type', False):
            if context.get('line_type', False) == 'customer':
                result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_form')
            else:
                result = mod_obj.get_object_reference(cr, uid, 'account_voucher', 'view_vendor_payment_form')
            result = result and result[1] or False
            view_id = result

        res = super(account_voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='partner_id']")
        if context.get('type', 'sale') in ('purchase', 'payment'):
            for node in nodes:
                node.set('domain', "[('supplier', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res

    def _compute_writeoff_amount(self, cr, uid, line_dr_ids, line_cr_ids, amount, voucher_date, context=None):
        if context is None:
            context = {}
        currency_pool = self.pool.get('res.currency')
        ctx = context.copy()
        counter_for_writeoff = counter_for_currency_diff = real_amount = 0.0
        ctx.update({'date': voucher_date})
        for l in line_dr_ids:
            real_amount -= l.get('amount_in_company_currency', 0.0)
            counter_for_writeoff -= currency_pool.compute(cr, uid, l['company_currency_id'], l['voucher_currency_id'], l.get('amount_in_company_currency',0.0), context=ctx)
            counter_for_currency_diff -= currency_pool.compute(cr, uid, l['currency_id'], l['company_currency_id'], l['amount'], context=ctx)
        for l in line_cr_ids:
            real_amount += l.get('amount_in_company_currency', 0.0)
            counter_for_writeoff += currency_pool.compute(cr, uid, l['company_currency_id'], l['voucher_currency_id'], l.get('amount_in_company_currency',0.0), context=ctx)
            counter_for_currency_diff += currency_pool.compute(cr, uid, l['currency_id'], l['company_currency_id'], l['amount'], context=ctx)
        writeoff_amount = amount - counter_for_writeoff
        currency_rate_difference = real_amount - counter_for_currency_diff
        return writeoff_amount, currency_rate_difference

    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_date, context=None):
        if not line_dr_ids and not line_cr_ids:
            return {'value':{}}
        line_osv = self.pool.get("account.voucher.line")
        line_dr_ids = resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount'], context)
        line_cr_ids = resolve_o2m_operations(cr, uid, line_osv, line_cr_ids, ['amount'], context)
        writeoff_amount, currency_rate_diff = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount, voucher_date, context=context)
        return {'value': {'writeoff_amount': writeoff_amount,}}# 'currency_rate_difference': currency_rate_diff}}

    def _get_writeoff_amount(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        if context is None:
            context = {}
        res = {}.fromkeys(ids,{})
        counter_for_writeoff = counter_for_currency_diff = real_amount = 0.0
        currency_pool = self.pool.get('res.currency')
        for voucher in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            for l in voucher.line_dr_ids:
                real_amount -= l.amount_in_company_currency
                counter_for_writeoff -= (l.voucher_currency_id.id == l.currency_id.id) and l.amount or l.amount_in_voucher_currency
                counter_for_currency_diff -= currency_pool.compute(cr, uid, l.currency_id.id, voucher.company_id.currency_id.id, l.amount, context=ctx)
            for l in voucher.line_cr_ids:
                real_amount += l.amount_in_company_currency
                counter_for_writeoff += (l.voucher_currency_id.id == l.currency_id.id) and l.amount or l.amount_in_voucher_currency
                counter_for_currency_diff += currency_pool.compute(cr, uid, l.currency_id.id, voucher.company_id.currency_id.id, l.amount, context=ctx)
            writeoff_amount = voucher.amount - counter_for_writeoff
            res[voucher.id]['writeoff_amount'] = writeoff_amount
            res[voucher.id]['currency_rate_difference'] = real_amount - counter_for_currency_diff
        return res

    def _currency_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            currency = voucher.journal_id.currency and voucher.journal_id.currency.id or voucher.company_id.currency_id.id
            res[voucher.id] = {'currency_id': currency, 'currency_id2': currency}
        return res

    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _order = "date desc, id desc"
    _columns = {
        'type':fields.selection([
            ('sale','Sale'),
            ('purchase','Purchase'),
            ('payment','Payment'),
            ('receipt','Receipt'),
        ],'Default Type', readonly=True, states={'draft':[('readonly',False)]}),
        'name':fields.char('Memo', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, select=True, states={'draft':[('readonly',False)]}, help="Effective date for accounting entries"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}, change_default=1),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'line_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'line_cr_ids':fields.one2many('account.voucher.line','voucher_id','Credits',
            domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'draft':[('readonly',False)]}),
        'line_dr_ids':fields.one2many('account.voucher.line','voucher_id','Debits',
            domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Notes', readonly=True, states={'draft':[('readonly',False)]}),
        'currency_id': fields.function(_currency_id, type='many2one', relation='res.currency', string='Currency', store=True, readonly=True, multi="currency"),
         #duplicated field for display purposes
        'currency_id2': fields.function(_currency_id, type='many2one', relation='res.currency', string='Currency', store=True, readonly=True, multi="currency"),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'company_currency': fields.related('company_id','currency_id', type='many2one', relation='res.currency', string='Currency', readonly=True),
        'state':fields.selection(
            [('draft','Draft'),
             ('proforma','Pro-forma'),
             ('posted','Posted'),
             ('cancel','Cancelled')
            ], 'State', readonly=True, size=32,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed Voucher. \
                        \n* The \'Pro-forma\' when voucher is in Pro-forma state,voucher does not have an voucher number. \
                        \n* The \'Posted\' state is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                        \n* The \'Cancelled\' state is used when user cancel voucher.'),
        'amount': fields.float('Total', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'tax_amount':fields.float('Tax Amount', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly',False)]}),
        'reference': fields.char('Ref #', size=64, readonly=True, states={'draft':[('readonly',False)]}, help="Transaction reference number."),
        'number': fields.char('Number', size=32, readonly=True,),
        'move_id':fields.many2one('account.move', 'Account Entry'),
        'move_ids': fields.related('move_id','line_id', type='one2many', relation='account.move.line', string='Journal Items', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft':[('readonly',False)]}),
        'audit': fields.related('move_id','to_check', type='boolean', help='Check this box if you are unsure of that journal entry and if you want to note it as \'to be reviewed\' by an accounting expert.', relation='account.move', string='To Review'),
        'pay_now':fields.selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'tax_id':fields.many2one('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}),
        'pre_line':fields.boolean('Previous Payments ?', required=False),
        'date_due': fields.date('Due Date', readonly=True, select=True, states={'draft':[('readonly',False)]}),
        'payment_option':fields.selection([
                                           ('without_writeoff', 'Keep Open'),
                                           ('with_writeoff', 'Reconcile'),
                                           ], 'Payment Difference', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'writeoff_acc_id': fields.many2one('account.account', 'Write-Off account', readonly=True, states={'draft': [('readonly', False)]}),
        'comment': fields.char('Write-Off Comment', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'analytic_id': fields.many2one('account.analytic.account','Write-Off Analytic Account', readonly=True, states={'draft': [('readonly', False)]}),
        'writeoff_amount': fields.function(_get_writeoff_amount, string='Write-Off Amount', type='float', readonly=True, multi="writeoff"),
        'currency_rate_difference': fields.function(_get_writeoff_amount, string="Currency Rate Difference", type='float', multi="writeoff"),
    }
    _defaults = {
        'period_id': _get_period,
        'partner_id': _get_partner,
        'journal_id':_get_journal,
        'currency_id': _get_currency,
        'reference': _get_reference,
        'narration':_get_narration,
        'amount': _get_amount,
        'type':_get_type,
        'state': 'draft',
        'pay_now': 'pay_later',
        'name': '',
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
        'tax_id': _get_tax,
        'payment_option': 'without_writeoff',
        'comment': _('Write-Off'),
    }

    def compute_tax(self, cr, uid, ids, context=None):
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        voucher_line_pool = self.pool.get('account.voucher.line')
        voucher_pool = self.pool.get('account.voucher')
        if context is None: context = {}

        for voucher in voucher_pool.browse(cr, uid, ids, context=context):
            voucher_amount = 0.0
            for line in voucher.line_ids:
                voucher_amount += line.untax_amount or line.amount
                line.amount = line.untax_amount or line.amount
                voucher_line_pool.write(cr, uid, [line.id], {'amount':line.amount, 'untax_amount':line.untax_amount})

            if not voucher.tax_id:
                self.write(cr, uid, [voucher.id], {'amount':voucher_amount, 'tax_amount':0.0})
                continue

            tax = [tax_pool.browse(cr, uid, voucher.tax_id.id, context=context)]
            partner = partner_pool.browse(cr, uid, voucher.partner_id.id, context=context) or False
            taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
            tax = tax_pool.browse(cr, uid, taxes, context=context)

            total = voucher_amount
            total_tax = 0.0

            if not tax[0].price_include:
                for tax_line in tax_pool.compute_all(cr, uid, tax, voucher_amount, 1).get('taxes', []):
                    total_tax += tax_line.get('amount', 0.0)
                total += total_tax
            else:
                for line in voucher.line_ids:
                    line_total = 0.0
                    line_tax = 0.0

                    for tax_line in tax_pool.compute_all(cr, uid, tax, line.untax_amount or line.amount, 1).get('taxes', []):
                        line_tax += tax_line.get('amount', 0.0)
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax
                    untax_amount = line.untax_amount or line.amount
                    voucher_line_pool.write(cr, uid, [line.id], {'amount':line_total, 'untax_amount':untax_amount})

            self.write(cr, uid, [voucher.id], {'amount':total, 'tax_amount':total_tax})
        return True

    def onchange_price(self, cr, uid, ids, line_ids, tax_id, partner_id=False, context=None):
        context = context or {}
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        line_pool = self.pool.get('account.voucher.line')
        res = {
            'tax_amount': False,
            'amount': False,
        }
        voucher_total = 0.0

        line_ids = resolve_o2m_operations(cr, uid, line_pool, line_ids, ["amount"], context)

        total = 0.0
        total_tax = 0.0
        for line in line_ids:
            line_amount = 0.0
            line_amount = line.get('amount',0.0)
            voucher_total += line_amount

        total = voucher_total
        total_tax = 0.0
        if tax_id:
            tax = [tax_pool.browse(cr, uid, tax_id, context=context)]
            if partner_id:
                partner = partner_pool.browse(cr, uid, partner_id, context=context) or False
                taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
                tax = tax_pool.browse(cr, uid, taxes, context=context)

            if not tax[0].price_include:
                for tax_line in tax_pool.compute_all(cr, uid, tax, voucher_total, 1).get('taxes', []):
                    total_tax += tax_line.get('amount')
                total += total_tax

        res.update({
            'amount':total or voucher_total,
            'tax_amount':total_tax
        })
        return {
            'value':res
        }

    def onchange_term_id(self, cr, uid, ids, term_id, amount):
        term_pool = self.pool.get('account.payment.term')
        terms = False
        due_date = False
        default = {'date_due':False}
        if term_id and amount:
            terms = term_pool.compute(cr, uid, term_id, amount)
        if terms:
            due_date = terms[-1][0]
            default.update({
                'date_due':due_date
            })
        return {'value':default}

    def onchange_journal_voucher(self, cr, uid, ids, line_ids=False, tax_id=False, price=0.0, partner_id=False, journal_id=False, ttype=False, context=None):
        """price
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        default = {
            'value':{},
        }

        if not partner_id or not journal_id:
            return default

        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        account_id = False
        tr_type = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
            tr_type = 'sale'
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
            tr_type = 'purchase'
        else:
            if not journal.default_credit_account_id or not journal.default_debit_account_id:
                raise osv.except_osv(_('Error !'), _('Please define default credit/debit account on the %s !') % (journal.name))
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
            tr_type = 'receipt'

        default['value']['account_id'] = account_id
        default['value']['type'] = ttype or tr_type

        vals = self.onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, context)
        default['value'].update(vals.get('value'))

        return default

    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, voucher_currency_id, ttype, date, context=None):
        """price
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        if not journal_id:
            return {}
        if context is None:
            context = {}
        context_multi_currency = context.copy()
        if date:
            context_multi_currency.update({'date': date})

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')
        #get default values
        vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context=context)
        vals = vals.get('value',{})
        voucher_currency_id = vals.get('currency_id', voucher_currency_id)
        default = {
            'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id': voucher_currency_id},
        }

        #drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', 'in', ids)]) or []
        if line_ids:
            line_pool.unlink(cr, uid, line_ids, context=context)

        if not partner_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        account_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id

        if journal.type not in ('cash', 'bank'):
            return default

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            account_type = 'receivable'

        if not context.get('move_line_ids', False):
            ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
        else:
            ids = context['move_line_ids']
        #order the lines by most old first
        ids.reverse()

        moves = move_line_pool.browse(cr, uid, ids, context=context)
        company_currency = journal.company_id.currency_id.id
        if company_currency != voucher_currency_id and ttype == 'payment':
            total_debit = currency_pool.compute(cr, uid, voucher_currency_id, company_currency, total_debit, context=context_multi_currency)
        elif company_currency != voucher_currency_id and ttype == 'receipt':
            total_credit = currency_pool.compute(cr, uid, voucher_currency_id, company_currency, total_credit, context=context_multi_currency)

        invoice_id = context.get('invoice_id', False)
        move_line_found = False
        for line in moves:
            if line.credit and line.reconcile_partial_id and ttype == 'receipt':
                continue
            if line.debit and line.reconcile_partial_id and ttype == 'payment':
                continue
            if invoice_id and line.move_id.invoice_id.id == invoice_id:
                move_line_found = line.id
                break
            if voucher_currency_id == company_currency:
                if line.amount_residual == price:
                    move_line_found = line.id
                    break
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0
            elif voucher_currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_line_found = line.id
                    break
                total_credit += line.amount_currency or 0.0
                total_debit += line.amount_currency or 0.0
        for line in moves:
            if line.credit and line.reconcile_partial_id and ttype == 'receipt':
                continue
            if line.debit and line.reconcile_partial_id and ttype == 'payment':
                continue
            original_amount = line.credit or line.debit or 0.0
            amount_original, amount_unreconciled = line_pool._get_amounts(cr, uid, line, context=context)
            currency_id = line.currency_id and line.currency_id.id or line.company_id.currency_id.id
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (move_line_found == line.id) and min(price, amount_unreconciled) or 0.0,
                'currency_id': currency_id,
                'voucher_currency_id': voucher_currency_id,
                'date_original':line.date,
                'company_currency_id': line.company_id.currency_id.id,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'amount_in_company_currency': 0.0,
            }

            if not move_line_found:
                #TODO: this part isn't working really: we should assign the voucher amount on only lines that are or the same currency
                if company_currency == voucher_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount
                elif voucher_currency_id == line.currency_id.id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount

            default['value']['line_ids'].append(rs)
            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'], default['value']['currency_rate_difference'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, date, context=context)
        return default

    def onchange_date(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        if context is None: context = {}
        period_pool = self.pool.get('account.period')
        res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=context)
        if context.get('invoice_id', False):
            company_id = self.pool.get('account.invoice').browse(cr, uid, context['invoice_id'], context=context).company_id.id
            context.update({'company_id': company_id})
        pids = period_pool.find(cr, uid, date, context=context)
        if pids:
            if not 'value' in res:
                res['value'] = {}
            res['value'].update({'period_id':pids[0]})
        return res

    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, context=None):
        if context is None: context = {}
        if not journal_id:
            return {}
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        tax_id = False
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id

        vals = self.onchange_price(cr, uid, ids, line_ids, tax_id, partner_id, context)
        vals['value'].update({'tax_id':tax_id})
        currency_id = journal.company_id.currency_id.id
        if journal.currency:
            currency_id = journal.currency.id
        vals['value'].update({'currency_id':currency_id})
        context.update({'company_id': journal.company_id.id})
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        if periods:
            vals['value'].update({'period_id':periods[0]})
        return vals

    def proforma_voucher(self, cr, uid, ids, context=None):
        self.action_move_line_create(cr, uid, ids, context=context)
        return True

    def action_cancel_draft(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for voucher_id in ids:
            wf_service.trg_create(uid, 'account.voucher', voucher_id, cr)
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def cancel_voucher(self, cr, uid, ids, context=None):
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')

        for voucher in self.browse(cr, uid, ids, context=context):
            recs = []
            for line in voucher.move_ids:
                if line.reconcile_id:
                    recs += [line.reconcile_id.id]
                if line.reconcile_partial_id:
                    recs += [line.reconcile_partial_id.id]

            reconcile_pool.unlink(cr, uid, recs)

            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
                move_pool.unlink(cr, uid, [voucher.move_id.id])
        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True

    def unlink(self, cr, uid, ids, context=None):
        for t in self.read(cr, uid, ids, ['state'], context=context):
            if t['state'] not in ('draft', 'cancel'):
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Voucher(s) which are already opened or paid !'))
        return super(account_voucher, self).unlink(cr, uid, ids, context=context)

    def onchange_payment(self, cr, uid, ids, pay_now, journal_id, partner_id, ttype='sale'):
        res = {}
        if not partner_id:
            return res
        res = {'account_id':False}
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        if pay_now == 'pay_later':
            partner = partner_pool.browse(cr, uid, partner_id)
            journal = journal_pool.browse(cr, uid, journal_id)
            if journal.type in ('sale','sale_refund'):
                account_id = partner.property_account_receivable.id
            elif journal.type in ('purchase', 'purchase_refund','expense'):
                account_id = partner.property_account_payable.id
            else:
                account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
            res['account_id'] = account_id
        return {'value':res}

    def action_move_line_create(self, cr, uid, ids, context=None):

        def _get_payment_term_lines(term_id, amount):
            term_pool = self.pool.get('account.payment.term')
            if term_id and amount:
                terms = term_pool.compute(cr, uid, term_id, amount)
                return terms
            return False
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        seq_obj = self.pool.get('ir.sequence')
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.move_id:
                continue
            context_multi_currency = context.copy()
            context_multi_currency.update({'date': voucher.date})

            if voucher.number:
                name = voucher.number
            else:
                name = seq_obj.get_id(cr, uid, voucher.journal_id.sequence_id.id)
            if not voucher.reference:
                ref = name.replace('/','')
            else:
                ref = voucher.reference

            move = {
                'name': name,
                'journal_id': voucher.journal_id.id,
                'narration': voucher.narration,
                'date': voucher.date,
                'ref': ref,
                'period_id': voucher.period_id and voucher.period_id.id or False
            }
            move_id = move_pool.create(cr, uid, move)

            #create the first line manually
            company_currency = voucher.journal_id.company_id.currency_id.id
            voucher_currency = voucher.currency_id.id
            debit = 0.0
            credit = 0.0
            if voucher.type in ('purchase', 'payment'):
                credit = currency_pool.compute(cr, uid, voucher_currency, company_currency, voucher.amount, context=context_multi_currency)
            elif voucher.type in ('sale', 'receipt'):
                debit = currency_pool.compute(cr, uid, voucher_currency, company_currency, voucher.amount, context=context_multi_currency)
            if debit < 0:
                credit = -debit
                debit = 0.0
            if credit < 0:
                debit = -credit
                credit = 0.0
            sign = debit - credit < 0 and -1 or 1
            #create the first line of the voucher
            move_line = {
                'name': voucher.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': voucher.account_id.id,
                'move_id': move_id,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'partner_id': voucher.partner_id.id,
                'currency_id': company_currency <> voucher_currency and  voucher_currency or False,
                'amount_currency': company_currency <> voucher_currency and sign * voucher.amount or 0.0,
                'date': voucher.date,
                'date_maturity': voucher.date_due
            }
            move_line_pool.create(cr, uid, move_line)

            #create the move line for the currency difference
            if voucher.currency_rate_difference:
                if voucher.currency_rate_difference > 0:
                    account_id = voucher.company_id.property_expense_currency_exchange
                    if not account_id:
                        raise osv.except_osv(_('Warning'),_("Unable to create accounting entry for currency rate difference. You have to configure the field 'Income Currency Rate' on the company! "))
                else:
                    account_id = voucher.company_id.property_income_currency_exchange
                    if not account_id:
                        raise osv.except_osv(_('Warning'),_("Unable to create accounting entry for currency rate difference. You have to configure the field 'Expense Currency Rate' on the company! "))

                currency_diff_line = {
                    'name': _('Currency Difference'),
                    'debit': voucher.currency_rate_difference > 0 and voucher.currency_rate_difference or 0.0,
                    'credit': voucher.currency_rate_difference < 0 and -voucher.currency_rate_difference or 0.0,
                    'account_id': account_id.id,
                    'move_id': move_id,
                    'journal_id': voucher.journal_id.id,
                    'period_id': voucher.period_id.id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'date_maturity': voucher.date_due
                }
                move_line_pool.create(cr, uid, currency_diff_line, context=context)

            rec_list_ids = []
            for line in voucher.line_ids:
                #create one move line per voucher line where amount is not 0.0
                if not line.amount:
                    continue
                #we check if the voucher line is fully paid or not and create a move line to balance the payment and initial invoice if needed
                if line.amount == line.amount_unreconciled:
                    amount = line.move_line_id.amount_residual #residual amount in company currency
                else:
                    amount = line.amount_in_company_currency
                move_line = {
                    'journal_id': voucher.journal_id.id,
                    'period_id': voucher.period_id.id,
                    'name': line.name or '/',
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'currency_id': company_currency <> line.currency_id.id and line.currency_id.id or False,
                    'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': voucher.date
                }
                if amount < 0:
                    amount = -amount
                    if line.type == 'dr':
                        line.type = 'cr'
                    else:
                        line.type = 'dr'
                if (line.type=='dr'):
                    move_line['debit'] = amount
                else:
                    move_line['credit'] = amount

                if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                    move_line.update({
                        'account_tax_id': voucher.tax_id.id,
                    })
                if move_line.get('account_tax_id', False):
                    tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                    if not (tax_data.base_code_id and tax_data.tax_code_id):
                        raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))
                sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                move_line['amount_currency'] = company_currency <> line.currency_id.id and sign * line.amount or 0.0
                voucher_line = move_line_pool.create(cr, uid, move_line)
                if line.move_line_id.id:
                    rec_ids = [voucher_line, line.move_line_id.id]
                    rec_list_ids.append(rec_ids)

            if not currency_pool.is_zero(cr, uid, voucher.currency_id, voucher.writeoff_amount):
                #create one line for the write off if needed
                diff = currency_pool.compute(cr, uid, voucher_currency, company_currency, voucher.writeoff_amount, context=context_multi_currency)
                account_id = False
                write_off_name = ''
                if voucher.payment_option == 'with_writeoff':
                    account_id = voucher.writeoff_acc_id.id
                    write_off_name = voucher.comment
                elif voucher.type in ('sale', 'receipt'):
                    account_id = voucher.partner_id.property_account_receivable.id
                else:
                    account_id = voucher.partner_id.property_account_payable.id
                move_line = {
                    'name': write_off_name or name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'debit': diff < 0 and -diff or 0.0,
                    'credit': diff > 0 and diff or 0.0,
                    'amount_currency': company_currency <> voucher_currency and -voucher.writeoff_amount or 0.0,
                    'currency_id': company_currency <> voucher_currency and voucher_currency or False,
                }
                move_line_pool.create(cr, uid, move_line)
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)
        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'number': False,
            'move_id': False,
            'line_cr_ids': False,
            'line_dr_ids': False,
            'reference': False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(account_voucher, self).copy(cr, uid, id, default, context)

account_voucher()

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _description = 'Voucher Lines'
    _order = "move_line_id"

    def _currency_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            move_line = line.move_line_id
            if move_line:
                res[line.id] = move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id
            else:
                res[line.id] = line.voucher_id.currency_id.id
        return res

    def _get_amounts(self, cr, uid, line_browse_rec, context=None):
        if line_browse_rec.currency_id:
            amount_original = line_browse_rec.amount_currency or 0.0
            amount_unreconciled = line_browse_rec.amount_residual_currency
        elif line_browse_rec.credit > 0:
            amount_original = line_browse_rec.credit or 0.0
            amount_unreconciled = line_browse_rec.amount_residual
        else:
            amount_original = line_browse_rec.debit or 0.0
            amount_unreconciled = line_browse_rec.amount_residual
        return amount_original, amount_unreconciled

    def _compute_balance(self, cr, uid, ids, name, args, context=None):
        currency_pool = self.pool.get('res.currency')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            amount_original, amount_unreconciled = self._get_amounts(cr, uid, line.move_line_id, context)
            res[line.id] = {
                'amount_original': amount_original,
                'amount_unreconciled': amount_unreconciled,
            }

        return res

    def __company_currency_amount(self, cr, uid, line, amount, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'date': line.date_original})
        currency_pool = self.pool.get('res.currency')
        amount_company_cur = currency_pool.compute(cr, uid, line.currency_id.id, line.company_currency_id.id, amount, context=ctx)
        ctx.update({'date': line.voucher_id.date})
        amount_voucher_cur = currency_pool.compute(cr, uid, line.currency_id.id, line.voucher_currency_id.id, amount, context=ctx)
        return amount_company_cur, amount_voucher_cur

    def onchange_amount(self, cr, uid, ids, amount, context=None):
        if not amount or not ids:
            return {'value':{'amount_in_company_currency': 0.0, 'amount_in_voucher_currency': 0.0}}
        for line in self.browse(cr, uid, ids, context=context):
            amount_company_cur, amount_voucher_cur  = self.__company_currency_amount(cr, uid, line, amount, context=context)
        return {'value': {'amount_in_company_currency': amount_company_cur, 'amount_in_voucher_currency': amount_voucher_cur}}

    def _get_amount_in_company_currency(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            amount_in_company_currency, amount_in_voucher_currency = self.__company_currency_amount(cr, uid, line, line.amount, context=context)
            res[line.id] = {
                 'amount_in_company_currency': amount_in_company_currency,
                 'amount_in_voucher_currency': amount_in_voucher_currency,
            }
        return res

    _columns = {
        'voucher_id':fields.many2one('account.voucher', 'Voucher', required=1, ondelete='cascade'),
        'move_line_id': fields.many2one('account.move.line', 'Journal Item'),
        'type':fields.selection([('dr','Debit'),('cr','Credit')], 'Dr/Cr'),
        'name':fields.char('Description', size=256),
        'account_id':fields.many2one('account.account','Account', required=True),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account'),
        'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
        'untax_amount':fields.float('Untax Amount'),

        'currency_id': fields.function(_currency_id, string='Currency', type='many2one', relation='res.currency'),
        'company_currency_id': fields.related('move_line_id','company_id','currency_id', type='many2one', relation='res.currency', string="Company Currency"),
        'voucher_currency_id': fields.related('voucher_id', 'currency_id', type='many2one', relation='res.currency', string="Voucher Currency"),

        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'amount_in_company_currency': fields.function(_get_amount_in_company_currency, string='Amount in Company Currency', type='float', digits_compute=dp.get_precision('Account'), multi="voucher_line_amount"),
        'amount_in_voucher_currency': fields.function(_get_amount_in_company_currency, string='Amount in Voucher Currency', type='float', digits_compute=dp.get_precision('Account'), multi="voucher_line_amount"),

        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly=1),
        'date_due': fields.related('move_line_id','date_maturity', type='date', relation='account.move.line', string='Due Date', readonly=1),
        'amount_original': fields.function(_compute_balance, multi='dc', type='float', string='Original Amount', store=True),
        'amount_unreconciled': fields.function(_compute_balance, multi='dc', type='float', string='Open Balance', store=True),
        'company_id': fields.related('voucher_id','company_id', relation='res.company', type='many2one', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'name': ''
    }

    def onchange_move_line_id(self, cr, user, ids, move_line_id, context=None):
        """
        Returns a dict that contains new values and context

        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.credit:
                ttype = 'dr'
            else:
                ttype = 'cr'
            account_id = move_line.account_id.id
            res.update({
                'account_id':account_id,
                'type': ttype
            })
        return {
            'value':res,
        }

    def default_get(self, cr, user, fields_list, context=None):
        """
        Returns default values for fields
        @param fields_list: list of fields, for which default values are required to be read
        @param context: context arguments, like lang, time zone

        @return: Returns a dict that contains default values for fields
        """
        if context is None:
            context = {}
        journal_id = context.get('journal_id', False)
        partner_id = context.get('partner_id', False)
        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')
        values = super(account_voucher_line, self).default_get(cr, user, fields_list, context=context)
        if (not journal_id) or ('account_id' not in fields_list):
            return values
        journal = journal_pool.browse(cr, user, journal_id, context=context)
        account_id = False
        ttype = 'cr'
        if journal.type in ('sale', 'sale_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            ttype = 'cr'
        elif journal.type in ('purchase', 'expense', 'purchase_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
            ttype = 'dr'
        elif partner_id:
            partner = partner_pool.browse(cr, user, partner_id, context=context)
            if context.get('type') == 'payment':
                ttype = 'dr'
                account_id = partner.property_account_payable.id
            elif context.get('type') == 'receipt':
                account_id = partner.property_account_receivable.id

        values.update({
            'account_id':account_id,
            'type':ttype
        })
        return values
account_voucher_line()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'

    def button_cancel(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')
        for st in self.browse(cr, uid, ids, context=context):
            voucher_ids = []
            for line in st.line_ids:
                if line.voucher_id:
                    voucher_ids.append(line.voucher_id.id)
            voucher_obj.cancel_voucher(cr, uid, voucher_ids, context)
        return super(account_bank_statement, self).button_cancel(cr, uid, ids, context=context)

    def create_move_from_st_line(self, cr, uid, st_line_id, company_currency_id, next_number, context=None):
        voucher_obj = self.pool.get('account.voucher')
        wf_service = netsvc.LocalService("workflow")
        move_line_obj = self.pool.get('account.move.line')
        bank_st_line_obj = self.pool.get('account.bank.statement.line')
        st_line = bank_st_line_obj.browse(cr, uid, st_line_id, context=context)
        if st_line.voucher_id:
            voucher_obj.write(cr, uid, [st_line.voucher_id.id], {'number': next_number, 'date': st_line.date}, context=context)
            if st_line.voucher_id.state == 'cancel':
                voucher_obj.action_cancel_draft(cr, uid, [st_line.voucher_id.id], context=context)
            wf_service.trg_validate(uid, 'account.voucher', st_line.voucher_id.id, 'proforma_voucher', cr)

            v = voucher_obj.browse(cr, uid, st_line.voucher_id.id, context=context)
            bank_st_line_obj.write(cr, uid, [st_line_id], {
                'move_ids': [(4, v.move_id.id, False)]
            })

            return move_line_obj.write(cr, uid, [x.id for x in v.move_ids], {'statement_id': st_line.statement_id.id, 'date': st_line.date}, update_check=False, context=context)
        return super(account_bank_statement, self).create_move_from_st_line(cr, uid, st_line.id, company_currency_id, next_number, context=context)

account_bank_statement()

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def _amount_reconciled(self, cursor, user, ids, name, args, context=None):
        if not ids:
            return {}

        res = {}
#        company_currency_id = False
        for line in self.browse(cursor, user, ids, context=context):
#            if not company_currency_id:
#                company_currency_id = line.company_id.id
            if line.voucher_id:
                res[line.id] = line.voucher_id.amount#
#                        res_currency_obj.compute(cursor, user,
#                        company_currency_id, line.statement_id.currency.id,
#                        line.voucher_id.amount, context=context)
            else:
                res[line.id] = 0.0
        return res

    def _check_amount(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.voucher_id:
                diff = abs(obj.amount) - obj.voucher_id.amount
                if not self.pool.get('res.currency').is_zero(cr, uid, obj.voucher_id.currency_id, diff):
                    return False
        return True

    _constraints = [
        (_check_amount, 'The amount of the voucher must be the same amount as the one on the statement line', ['amount']),
    ]

    _columns = {
        'amount_reconciled': fields.function(_amount_reconciled,
            string='Amount reconciled', type='float'),
        'voucher_id': fields.many2one('account.voucher', 'Payment'),

    }

    def unlink(self, cr, uid, ids, context=None):
        voucher_obj = self.pool.get('account.voucher')
        statement_line = self.browse(cr, uid, ids, context=context)
        unlink_ids = []
        for st_line in statement_line:
            if st_line.voucher_id:
                unlink_ids.append(st_line.voucher_id.id)
        voucher_obj.unlink(cr, uid, unlink_ids, context=context)
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

account_bank_statement_line()

def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

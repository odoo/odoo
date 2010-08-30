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
import netsvc
from osv import fields
from osv import osv
from tools.translate import _

class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    def _unreconciled(self, cr, uid, ids, prop, unknow_none, context):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.debit - line.credit
            if line.reconcile_partial_id:
                res[line.id] = 0
                for partial in line.reconcile_partial_id.line_partial_ids:
                    res[line.id] += partial.debit - partial.credit
            res[line.id] = abs(res[line.id])
        return res

    _columns = {
        'amount_unreconciled': fields.function(_unreconciled, method=True, string='Unreconciled Amount'),
    }
account_move_line()

class account_voucher(osv.osv):
    def _get_type(self, cr, uid, ids, context={}):
        return context.get('type')
        
    def _get_period(self, cr, uid, context={}):
        if context.get('period_id', False):
            return context.get('period_id')
        periods = self.pool.get('account.period').find(cr, uid)
        return periods and periods[0] or False

    def _get_journal(self, cr, uid, context={}):
        journal_pool = self.pool.get('account.journal')
        if context.get('journal_id', False):
            return context.get('journal_id')
        ttype = context.get('type', 'bank')
        res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)
        return res and res[0] or False

    def _get_tax(self, cr, uid, context={}):
        journal_id = context.get('journal_id', False)
        if not journal_id:
            return False
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
            return tax_id
        return False

    def _get_currency(self, cr, uid, context):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if user.company_id:
            return user.company_id.currency_id.id
        return False

    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _order = "date desc, id desc"
    _rec_name = 'number'
    _columns = {
        'type':fields.selection([
            ('sale','Sale'),
            ('purchase','Purchase'),
            ('payment','Payment'),
            ('receipt','Receipt'),
        ],'Type'),
        'name':fields.char('Memo', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, states={'draft':[('readonly',False)]}, help="Effective date for accounting entries"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}),

        'line_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'line_cr_ids':fields.one2many('account.voucher.line','voucher_id','Credits',
            domain=[('type','=','cr')], context={'default_type':'cr'}, readonly=True, states={'draft':[('readonly',False)]}),
        'line_dr_ids':fields.one2many('account.voucher.line','voucher_id','Debits',
            domain=[('type','=','dr')], context={'default_type':'dr'}, readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Narration', readonly=True, states={'draft':[('readonly',False)]}),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True),
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
        'amount': fields.float('Total', digits=(16, 2), required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'tax_amount':fields.float('Tax Amount', digits=(14,2), readonly=True, states={'draft':[('readonly',False)]}),
        'reference': fields.char('Ref #', size=64, readonly=True, states={'draft':[('readonly',False)]}, help="Payment or Receipt transaction number, i.e. Bank cheque number or payorder number or Wire transfer number or Acknowledge number."),
        'number': fields.related('move_id', 'name', type="char", readonly=True, string='Number'),
        'move_id':fields.many2one('account.move', 'Account Entry'),
        'move_ids': fields.related('move_id','line_id', type='many2many', relation='account.move.line', string='Journal Items', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}),
        'audit': fields.related('move_id','to_check', type='boolean', relation='account.move', string='Audit Complete ?'),
        'pay_now':fields.selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'tax_id':fields.many2one('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}),
        'pre_line':fields.boolean('Previous Payments ?', required=False),
        'date_due': fields.date('Due Date'),
        'term_id':fields.many2one('account.payment.term', 'Term', required=False),
    }
    _defaults = {
        'period_id': _get_period,
        'journal_id':_get_journal,
        'currency_id': _get_currency,
        'type':_get_type,
        'state': lambda *a: 'draft',
        'pay_now':lambda *a: 'pay_later',
        'name': lambda *a: '',
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
        'tax_id': _get_tax,
    }

    # TODO: review this code.
    def onchange_price(self, cr, uid, ids, line_ids, tax_id, partner_id=False, context={}):
        tax_pool = self.pool.get('account.tax')
        partner_pool = self.pool.get('res.partner')
        position_pool = self.pool.get('account.fiscal.position')
        voucher_line_pool = self.pool.get('account.voucher.line')
        res = {
            'tax_amount':False,
            'amount':False,
        }
        voucher_total_tax = 0.0
        voucher_total = 0.0
        voucher_line_ids = []
        
        total = 0.0
        total_tax = 0.0
        
        for line in line_ids:
            voucher_line_ids += [line[1]]
            voucher_total += line[2].get('amount')
        
        total = voucher_total
        
        if tax_id:
            tax = [tax_pool.browse(cr, uid, tax_id)]
            
            if partner_id:
                partner = partner_pool.browse(cr, uid, partner_id) or False
                taxes = position_pool.map_tax(cr, uid, partner and partner.property_account_position or False, tax)
                tax = tax_pool.browse(cr, uid, taxes)
            
            if not tax[0].price_include:
                for tax_line in tax_pool.compute_all(cr, uid, tax, voucher_total, 1).get('taxes'):
                    total_tax += tax_line.get('amount')
                total += total_tax
            else:
                line_ids2 = []
                for line in line_ids:
                    line_total = 0.0
                    line_tax = 0.0
                    operation = line[0]
                    rec_id = line[1]
                    rec = line[2]
                    for tax_line in tax_pool.compute_all(cr, uid, tax, rec.get('amount'), 1).get('taxes'):
                        line_tax += tax_line.get('amount')
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax
                    if rec_id:
                        voucher_line_pool.write(cr, uid, [rec_id], {'amount':line_total})
                        line_ids2 += [rec_id]
                    else:
                        rec.update({
                            'amount':line_total
                        })
                res.update({
                    'line_ids':line_ids2
                })
        res.update({
            'amount':total,
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
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id=False, price=0.0, ttype=False, context={}):
        """price
        Returns a dict that contains new values and context
    
        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        
        @return: Returns a dict which contains new values, and context
        """
        if not journal_id:
            return {}
        move_pool = self.pool.get('account.move')
        line_pool = self.pool.get('account.voucher.line')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        default = {
            'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False},
        }

        if not partner_id:
            return default

        if not partner_id and ids:
            line_ids = line_pool.search(cr, uid, [('voucher_id','=',ids[0])])
            if line_ids:
                line_pool.unlink(cr, uid, line_ids)
            return default

        journal = journal_pool.browse(cr, uid, journal_id)
        partner = partner_pool.browse(cr, uid, partner_id)
        account_id = False
        term_id = False
        if journal.type in ('sale','sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund','expense'):
            term_id = partner.property_payment_term.id
            if term_id:
                vals = self.onchange_term_id(cr, uid, ids, term_id, price)
                default['value'].update(vals.get('value'))
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
        default['value'].update({
            'account_id':account_id,
            'term_id':term_id
        })
        if journal.type not in ('cash', 'bank'):
            return default
        
        account_type = 'receivable'
        if ttype == 'payment':
            account_type = 'payable'
        else:
            account_type = 'receivable'
            
        ids = move_line_pool.search(cr, uid, [('account_id.type','=', account_type), ('reconcile_id','=', False), ('partner_id','=',partner_id)], context=context)
        moves = move_line_pool.browse(cr, uid, ids)
        total_credit = price or 0.0
        total_debit = 0.0
        for line in moves:
            if line.credit and line.reconcile_partial_id:
                continue
            total_credit += line.credit or 0.0
            total_debit += line.debit or 0.0
        for line in moves:
            if line.credit and line.reconcile_partial_id:
                continue
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original':line.credit or line.debit or 0.0,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': line.amount_unreconciled
            }
            if line.credit:
                rs['amount'] = min(line.amount_unreconciled, total_debit)
                total_debit -= rs['amount']
            else:
                rs['amount'] = min(line.debit, total_credit)
                total_credit -= rs['amount']

            default['value']['line_ids'].append(rs)
            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)
            
            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1                

        return default

    def onchange_date(self, cr, user, ids, date, context={}):
        """
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        period_pool = self.pool.get('account.period')
        pids = period_pool.search(cr, user, [('date_start','<=',date), ('date_stop','>=',date)])
        if not pids:
            return {}
        return {
            'value':{
                'period_id':pids[0]
            }
        }

    def onchange_journal(self, cr, uid, ids, journal_id):
        return {}

    def proforma_voucher(self, cr, uid, ids):
        self.action_move_line_create(cr, uid, ids)
        return True

    def action_cancel_draft(self, cr, uid, ids, context={}):
        wf_service = netsvc.LocalService("workflow")
        for voucher_id in ids:
            wf_service.trg_create(uid, 'account.voucher', voucher_id, cr)
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def cancel_voucher(self, cr, uid, ids, context={}):
        move_pool = self.pool.get('account.move')
        voucher_line_pool = self.pool.get('account.voucher.line')
        for voucher in self.browse(cr, uid, ids):
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

    # TODO
    def onchange_payment(self, cr, uid, ids, pay_now, journal_id, partner_id, ttype='sale'):
        if not partner_id:
            return {}
        partner_pool = self.pool.get('res.partner')
        res = {'account_id':False}
        if pay_now == 'pay_later':
            partner = partner_pool.browse(cr, uid, partner_id)
            if ttype == 'sale':
                res.update({
                    'account_id':partner.property_account_receivable.id,
                })
            elif ttype == 'purchase':
                res.update({
                    'account_id':partner.property_account_payable.id,
                })
        return {
            'value':res
        }

    def action_move_line_create(self, cr, uid, ids, *args):
    
        def _get_payment_term_lines(term_id, amount):
            term_pool = self.pool.get('account.payment.term')
            if term_id and amount:
                terms = term_pool.compute(cr, uid, term_id, amount)
                return terms
            return False
    
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        analytic_pool = self.pool.get('account.analytic.line')
        currency_pool = self.pool.get('res.currency')
        invoice_pool = self.pool.get('account.invoice')
        
        for inv in self.browse(cr, uid, ids):
            if inv.move_id:
                continue

            if not inv.line_ids:
                raise osv.except_osv(_('Error !'), _('You can not validate a voucher without lines !'))

            if inv.journal_id.sequence_id:
                name = self.pool.get('ir.sequence').get_id(cr, uid, inv.journal_id.sequence_id.id)
            else:
                raise osv.except_osv(_('Error !'), _('Please define a sequence on the journal !'))

            move = {
                'name' : name,
                'journal_id': inv.journal_id.id,
                'narration' : inv.narration,
                'date':inv.date,
                'ref':inv.reference,
                'period_id': inv.period_id and inv.period_id.id or False
            }
            move_id = move_pool.create(cr, uid, move)
            company_currency = inv.account_id.company_id.currency_id.id
            
            #create the first line manually
            debit = 0.0
            credit = 0.0
            # TODO: is there any other alternative then the voucher type ??
            if inv.type in ('purchase', 'payment'):
                credit = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.amount)
            elif inv.type in ('sale', 'receipt'):
                debit = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.amount)
            
            if inv.type == 'purchase' and inv.term_id and _get_payment_term_lines(inv.term_id.id, credit or debit):
                terms = _get_payment_term_lines(inv.term_id.id, credit or debit)
                for term in terms:
                    due_date = term[0]
                    amount = term[1]
                    move_line = {
                        'name':inv.name or '/',
                        'debit':0.0,
                        'credit':amount,
                        'date_maturity':due_date,
                        'account_id':inv.account_id.id,
                        'move_id':move_id ,
                        'journal_id':inv.journal_id.id,
                        'period_id':inv.period_id.id,
                        'partner_id':inv.partner_id.id,
                        'currency_id':inv.currency_id.id,
                        'date':inv.date
                    }
                    master_line = move_line_pool.create(cr, uid, move_line)
            else:
                move_line = {
                    'name':inv.name or '/',
                    'debit':debit,
                    'credit':credit,
                    'account_id':inv.account_id.id,
                    'move_id':move_id ,
                    'journal_id':inv.journal_id.id,
                    'period_id':inv.period_id.id,
                    'partner_id':inv.partner_id.id,
                    'currency_id':inv.currency_id.id,
                    'date':inv.date
                }
                master_line = move_line_pool.create(cr, uid, move_line)

            rec_list_ids = []
            line_total = debit - credit
            for line in inv.line_ids:
                if not line.amount:
                    continue
                amount = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, line.amount)
                move_line = {
                    'name':line.name and line.name or '/',
                    'account_id':line.account_id.id,
                    'move_id':move_id,
                    'partner_id':inv.partner_id.id,
                    'currency_id':inv.currency_id.id,
                }
                if (line.type=='dr'):
                    line_total += amount
                    move_line['debit'] = amount
                else:
                    line_total -= amount
                    move_line['credit'] = amount

                master_line = move_line_pool.create(cr, uid, move_line)
                if line.move_line_id.id:
                    rec_ids = [master_line, line.move_line_id.id]
                    rec_list_ids.append(rec_ids)

            if inv.tax_amount > 0:
                amount = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.tax_amount)
                name = inv.tax_id and inv.tax_id.name or '/'
                move_line = {
                    'name':name,
                    'move_id':move_id ,
                    'journal_id':inv.journal_id.id,
                    'period_id':inv.period_id.id,
                    'partner_id':inv.partner_id.id,
                    'currency_id':inv.currency_id.id,
                }

                if inv.journal_id.type in ('sale','purchase_refund'):
                    line_total -= amount
                    move_line['credit'] = amount
                else:
                    line_total += amount
                    move_line['debit'] = amount

                account_id = False
                if inv.tax_id:
                    if inv.journal_id.type in ('sale_refund','purchase_refund'):
                        account_id = inv.tax_id.account_paid_id
                    else:
                        account_id = inv.tax_id.account_collected_id.id
                if not account_id:
                    raise osv.except_osv(_('Invalid Error !'), _('No account defined on the related tax !'))
                move_line['account_id'] = account_id

                move_line_id = move_line_pool.create(cr, uid, move_line)
            
            if not self.pool.get('res.currency').is_zero(cr, uid, inv.currency_id, line_total):
                diff = line_total
                move_line = {
                    'name':name,
                    'account_id':False,
                    'move_id':move_id ,
                    'partner_id':inv.partner_id.id,
                    'date':inv.date,
                    'credit':diff>0 and diff or 0.0,
                    'debit':diff<0 and -diff or 0.0,
                }
                account_id = False
                if inv.journal_id.type in ('sale','sale_refund', 'cash','bank'):
                    account_id = inv.partner_id.property_account_receivable.id
                else:
                    account_id = inv.partner_id.property_account_payable.id
                move_line['account_id'] = account_id
                move_line_id = move_line_pool.create(cr, uid, move_line)

            self.write(cr, uid, [inv.id], {
                'move_id': move_id,
                'state':'posted'
            })
            move_pool.post(cr, uid, [move_id], context={})
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    move_line_pool.reconcile_partial(cr, uid, rec_ids)
        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state':'draft',
            'number':False,
            'move_id':False
        })
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(account_voucher, self).copy(cr, uid, id, default, context)

    # TODO
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Returns views and fields for current model where view will depend on {view_type}.
        @param view_id: list of fields, which required to read signatures
        @param view_type: defines a view type. it can be one of (form, tree, graph, calender, gantt, search, mdx)
        @param context: context arguments, like lang, time zone
        @param toolbar: contains a list of reports, wizards, and links related to current model
        
        @return: Returns a dict that contains definition for fields, views, and toolbars
        """
        data_pool = self.pool.get('ir.model.data')
        journal_pool = self.pool.get('account.journal')
        voucher_type = {
            'sale':'view_sale_receipt_form',
            'purchase':'view_purchase_receipt_form',
            'payment':'view_vendor_payment_form',
            'receipt':'view_vendor_receipt_form'
        }
        if view_type == 'form':
            tview = voucher_type.get(context.get('type'))
            result = data_pool._get_id(cr, uid, 'account_voucher', tview)
            view_id = data_pool.browse(cr, uid, result, context=context).res_id
        
        res = super(account_voucher, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        
        #Restrict the list of journal view in search view
        if view_type == 'search':
            journal_list = journal_pool.name_search(cr, uid, '', [], context=context)
            res['fields']['journal_id']['selection'] = journal_list
        return res

account_voucher()

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _description = 'Voucher Lines'
    def _compute_balance(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            move_line = line.move_line_id or False
            if not move_line:
                res[line.id] = 0.0
            elif move_line and move_line.credit > 0:
                res[line.id] = move_line.credit
            else:
                res[line.id] = move_line.debit
        return res

    _columns = {
        'voucher_id':fields.many2one('account.voucher', 'Voucher', required=1, ondelete='cascade'),
        'name':fields.char('Description', size=256),
        'account_id':fields.many2one('account.account','Account', required=True),
        'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
        'amount':fields.float('Amount'),
        'type':fields.selection([('dr','Debit'),('cr','Credit')], 'Cr/Dr'),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account'),
        'move_line_id': fields.many2one('account.move.line', 'Journal Item'),
        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly=1),
        'date_due': fields.related('move_line_id','date_maturity', type='date', relation='account.move.line', string='Due Date', readonly=1),
        'amount_original': fields.function(_compute_balance, method=True, type='float', string='Originial Amount', store=True),
        'amount_unreconciled': fields.related('move_line_id','amount_unreconciled', type='float', relation='account.move.line', string='Open Balance', readonly="1"),
    }
    _defaults = {
        'name': lambda *a: ''
    }

    def onchange_move_line_id(self, cr, user, ids, move_line_id, context={}):
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
            move_id = move_line.move_id.id
            if move_line.credit:
                ttype='dr'
                amount = move_line.credit
            else:
                ttype='cr'
                amount = move_line.debit
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
        journal_id = context.get('journal_id', False)
        partner_id = context.get('partner_id', False)
        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')
        values = super(account_voucher_line, self).default_get(cr, user, fields_list, context=context)
        if (not journal_id) or ('account_id' not in fields_list):
            return values
        journal = journal_pool.browse(cr, user, journal_id)
        account_id = False
        if journal.type in ('sale', 'purchase_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
        elif journal.type in ('purchase', 'expense', 'sale_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
        elif partner_id:
            partner = partner_pool.browse(cr, user, partner_id, context=context)
            if context.get('type') == 'payment':
                account_id = partner.property_account_payable.id
            elif context.get('type') == 'receipt':
                account_id = partner.property_account_receivable.id

        if (not account_id) and 'account_id' in fields_list:
            raise osv.except_osv(_('Invalid Error !'), _('Please change partner and try again !'))
        values.update({
            'account_id':account_id,
        })
        return values
account_voucher_line()

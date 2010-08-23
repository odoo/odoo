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

class ir_sequence_type(osv.osv):
    _inherit = "ir.sequence.type"
    _columns = {
        'name': fields.char('Sequence Name',size=128, required=True),
        'code': fields.char('Sequence Code',size=128, required=True),
    }
ir_sequence_type()

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'max_amount': fields.float('Verify Transaction', digits=(16, 2), help="Validate voucher entry twice before posting it, if transaction amount more then entered here"),
    }
account_journal()

class account_account(osv.osv):
    """
    account_account
    """
    
    _inherit = 'account.account'
    _columns = {
        'user_type_type': fields.related('user_type','report_type', type='char', size=64, relation='account.account.type', string='User Type Code', readonly=True, store=True)
    }
account_account()

class account_move(osv.osv):
    _inherit = 'account.move'
    
    def _get_line_ids(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            result[line.move_id.id] = True
        return result.keys()
    
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            rs = {
                'reconcile_id': False,
            }
            for line in move.line_id:
                if line.reconcile_id:
                    rs.update({
                        'reconcile_id': line.reconcile_id.id
                    })
                    break
            res[move.id] = rs
        return res
    
    _columns = {
        'reconcile_id': fields.function(_amount_all, method=True, type="many2one", relation="account.move.reconcile", select=True, string='Reconcile',
            store=True,
            multi='all'),
    }
    
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        """
        Returns a list of ids based on search domain {args}
    
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param args: list of conditions to be applied in search opertion
        @param offset: default from first record, you can start from nth record
        @param limit: number of records to be obtained as a result of search opertion
        @param order: ordering on any field(s)
        @param context: context arguments, like lang, time zone
        @param count: 
        
        @return: Returns a list of ids based on search domain
        """
        if not context:
            context = {}
        ttype = context.get('type', False)
        partner = context.get('partner_id', False)
        voucher = context.get('voucher', False)
        if voucher and not partner:
            raise osv.except_osv(_('Invalid Partner !'), _('Please select the partner !'))
            
        if ttype and ttype in ('receipt'):
            args += [('journal_id.type','in', ['sale', 'purchase_refund'])]
        elif ttype and ttype in ('payment'):
            args += [('journal_id.type','in', ['purchase', 'sale_refund'])]
        elif ttype and ttype in('sale', 'purchase'):
            raise osv.except_osv(_('Invalid action !'), _('You can not reconcile sales, purchase, or journal voucher with invoice !'))
            args += [('journal_id.type','=', 'do_not_allow_search')]
        res = super(account_move, self).search(cr, user, args, offset, limit, order, {}, count)
        return res
    
account_move()

class account_voucher(osv.osv):

    def _get_period(self, cr, uid, context={}):
        if context.get('period_id', False):
            return context.get('period_id')

        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    def _get_journal(self, cr, uid, context={}):
        journal_pool = self.pool.get('account.journal')

        if context.get('journal_id', False):
            return context.get('journal_id')

        ttype = context.get('type', 'bank')
        res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)

        if res:
            return res[0]
        else:
            return False

    def _get_type(self, cr, uid, context={}):
        return context.get('type')
        
    def _get_pay_journal(self, cr, uid, context={}):
        journal_pool = self.pool.get('account.journal')

        res = journal_pool.search(cr, uid, [('type', '=', 'bank')], limit=1)
        if res:
            return res[0]
        else:
            return False

    def _get_currency(self, cr, uid, context):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return self.pool.get('res.currency').search(cr, uid, [('rate','=',1.0)])[0]

    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _order = "id desc"
    _rec_name = 'number'
    
    _columns = {
        'type':fields.selection([
            ('payment','Payment'),
            ('receipt','Receipt'),
            ('sale','Sale'),
            ('purchase','Purchase'), 
        ],'Type', select=True, readonly=True),
        'name':fields.char('Memo', size=256, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, states={'draft':[('readonly',False)]}, help="Effective date for accounting entries"),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'payment_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'narration':fields.text('Narration', readonly=True, states={'draft':[('readonly',False)]}),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'state':fields.selection(
            [('draft','Draft'),
             ('proforma','Pro-forma'),
             ('posted','Posted'),
             ('recheck','Waiting for Re-checking'),
             ('cancel','Cancel'),
             ('audit','Audit Complete')
            ], 'State', readonly=True, size=32,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed Voucher. \
                        \n* The \'Pro-forma\' when voucher is in Pro-forma state,voucher does not have an voucher number. \
                        \n* The \'Posted\' state is used when user create voucher,a voucher number is generated and voucher entries are created in account \
                        \n* The \'Cancelled\' state is used when user cancel voucher.'),
        #'amount': fields.function(_compute_total, method=True, type='float', digits=(14,2), string='Total', store=True),
        'amount': fields.float('Total', digits=(16, 2), readonly=True, states={'draft':[('readonly',False)]}),
        'tax_amount':fields.float('Tax Amount', digits=(14,4), readonly=True, states={'draft':[('readonly',False)]}),
        'reference': fields.char('Ref #', size=64, readonly=True, states={'draft':[('readonly',False)]}, help="Payment or Receipt transaction number, i.e. Bank cheque number or payorder number or Wire transfer number or Acknowledge number."),
        'number': fields.related('move_id', 'name', type="char", readonly=True, string='Number'),
        'move_id':fields.many2one('account.move', 'Account Entry'),
        'move_ids': fields.related('move_id','line_id', type='many2many', relation='account.move.line', string='Journal Items', readonly=True, states={'draft':[('readonly',False)]}),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]}),
        'audit': fields.related('move_id','to_check', type='boolean', relation='account.move', string='Audit Complete ?'),
        'pay_now':fields.selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'tax_id':fields.many2one('account.tax', 'Tax', readonly=True, states={'draft':[('readonly',False)]}),
    }
    
    _defaults = {
        'type':_get_type,
        'period_id': _get_period,
        'journal_id':_get_journal,
        'currency_id': _get_currency,
        'state': lambda *a: 'draft',
        'pay_now':lambda *a: 'pay_later',
        'name': lambda *a: '',
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
        'audit': lambda *a: False,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
    }
    
    def onchange_price(self, cr, uid, ids, payment_ids, tax_amount, tax_id, context={}):
        res = {
            'tax_amount':False,
            'amount':False
        }
        tax_pool = self.pool.get('account.tax')
        total = 0.0
        
        for line in payment_ids:
            total += line[2].get('amount')
        
        if tax_id:
            tax = tax_pool.browse(cr, uid, tax_id)
            if tax.type == 'percent':
                tax_amount = total * tax_amount and tax_amount or tax.amount
            if tax.type == 'fixed':
                tax_amount = tax_amount and tax_amount or tax.amount

        res.update({
            'amount':total + tax_amount,
            'tax_amount':tax_amount
        })
        
        return {
            'value':res
        }

    def create(self, cr, uid, vals, context={}):
        """
        Create a new record for a model account_voucher
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param vals: provides data for new record
        @param context: context arguments, like lang, time zone
        
        @return: Returns an id of the new record
        """

        old_line = []
        new_lines = []
        
        payment_ids = vals.get('payment_ids')
        
        if not payment_ids:
            payment_ids = []
        
        vals.update({
            'payment_ids':False
        })
        for line in payment_ids:
            id1 = line[0]
            id2 = line[1]
            res = line[2]
            if id1 == 0 and id2 == 0:
                new_lines += [(id1, id2, res)]
            else:
                old_line += [(id1, id2, res)]

        if new_lines:
            vals.update({
                'payment_ids':new_lines
            })

        res_id = super(account_voucher, self).create(cr, uid, vals, context)
        
        if old_line:
            new_payment_ids = []
            for line in old_line:
                id1 = line[0]
                id2 = line[1]
                res = line[2]
                if res:
                    res.update({
                        'voucher_id':res_id
                    })
                    new_payment_ids += [(id1, id2, res)]
                
            self.write(cr, uid, [res_id], {'payment_ids':new_payment_ids})
        return res_id
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, ttype, journal_id=False, context={}):
        """
        Returns a dict that contains new values and context
    
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        
        @return: Returns a dict which contains new values, and context
        """
        move_pool = self.pool.get('account.move')
        line_pool = self.pool.get('account.voucher.line')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        res = []
        
        context.update({
            'type':ttype, 
            'partner_id':partner_id, 
            'voucher':True,
        })
        if journal_id:
            context.update({
                'journal_id':journal_id, 
            })
        
        default = {
            'value':{},
            'context':context,
        }
        if not partner_id or not ttype:
            if ids:
                line_ids = line_pool.search(cr, uid, [('voucher_id','=',ids[0])])
                if line_ids:
                    line_pool.unlink(cr, uid, line_ids)
            return default
        
        account_id = False
        partner = partner_pool.browse(cr, uid, partner_id)
        if ttype in ('sale'):
            account_id = partner.property_account_receivable.id
        elif ttype in ('purchase'):
            account_id = partner.property_account_payable.id
        elif ttype in ('payment', 'receipt'):
            journal = journal_pool.browse(cr, uid, journal_id)
            if ttype == 'payment':
                account_id = journal.default_credit_account_id.id
            elif ttype == 'receipt':
                account_id = journal.default_debit_account_id.id
        
        default['value'].update({
            'account_id':account_id
        })
        if ttype not in ('payment', 'receipt'):
            return default
        
        voucher_id = ids and ids[0] or False
        search_type = 'credit'
        account_type = False
        if ttype == 'receipt':
            search_type = 'debit'
            account_type = 'receivable'
        elif ttype == 'payment':
            search_type = 'credit'
            account_type = 'payable'

        ids = move_line_pool.search(cr, uid, [('account_id.type','=', account_type), ('reconcile_id','=', False), ('partner_id','=',partner_id), (search_type,'>',0)], context=context)
        total = 0.0
        for line in move_line_pool.browse(cr, uid, ids):
            amount = 0.0
            rs = move_line_pool.default_get(cr, uid, move_line_pool._columns.keys(), context=context)
            rs.update({
                'name':line.move_id.name,
                'ref':line.ref or '/',
                'move_id':line.move_id.id,
                'move_line_id':line.id,
                'voucher_id':voucher_id,
                'amount':amount,
            })
            
            if ttype == 'payment':
                rs.update({
                    'account_id':line.move_id.partner_id.property_account_payable.id,
                    #'amount':line.credit
                })
                amount = line.credit
            elif ttype == 'receipt':
                rs.update({
                    'account_id':line.move_id.partner_id.property_account_receivable.id,
                    #'amount':line.debit
                })
                amount = line.debit

            total += amount
            line_id = line_pool.create(cr, uid, rs, context=context)
            res += [line_id]

        res = {
            'payment_ids':res, 
            'account_id':account_id, 
            'amount':total
        }
        return {
            'value':res,
            'context':context,
        }
    
    def onchange_date(self, cr, user, ids, date, context={}):
        """
        Returns a dict that contains new values and context
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        res = {}
        period_pool = self.pool.get('account.period')
        pids = period_pool.search(cr, user, [('date_start','<=',date), ('date_stop','>=',date)])
        if pids:
            res.update({
                'period_id':pids[0]
            })
            context.update({
                'period_id':pids[0]
            })
        return {
            'value':res,
            'context':context,
        }
    
    def onchange_journal(self, cr, uid, ids, journal_id, ttype):
        res = {}

        if not journal_id:
            return {
                'value':res
            }
        journal_pool = self.pool.get('account.journal')
        journal = journal_pool.browse(cr, uid, journal_id)

        if journal.type in ('sale', 'purchase') and not ttype:
            res.update({
                'type':journal.type
            })

        return {
            'value':res
        }

    def voucher_recheck(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'recheck'}, context)
        return True

    def proforma_voucher(self, cr, uid, ids, context={}):
        self.action_move_line_create(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'posted'})
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

            line_ids = voucher_line_pool.search(cr, uid, [('voucher_id','=',voucher.id), ('is_tax','=',True)])
            if line_ids:
                voucher_line_pool.unlink(cr, uid, line_ids)

        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True

    def unlink(self, cr, uid, ids, context=None):
        vouchers = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in vouchers:
            if t['state'] in ('draft', 'cancel'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv('Invalid action !', 'Cannot delete Voucher(s) which are already opened or paid !')
        return super(account_voucher, self).unlink(cr, uid, unlink_ids, context=context)

    def onchange_payment(self, cr, uid, ids, pay_now, journal_id, partner_id, ttype):
        partner_pool = self.pool.get('res.partner')

        res = {'account_id':False}
        
        if pay_now == 'pay_later' and ttype in ('sale', 'purchase'):
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
    
        journal_pool = self.pool.get('account.journal')
        sequence_pool = self.pool.get('ir.sequence')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        analytic_pool = self.pool.get('account.analytic.line')
        currency_pool = self.pool.get('res.currency')
        invoice_pool = self.pool.get('account.invoice')
        
        for inv in self.browse(cr, uid, ids):
        
            if inv.move_id:
                continue

            if not inv.payment_ids:
                raise osv.except_osv(_('Error !'), _('Please define lines on voucher !'))
            
            journal = journal_pool.browse(cr, uid, inv.journal_id.id)
            if journal.sequence_id:
                name = sequence_pool.get_id(cr, uid, journal.sequence_id.id)
            else:
                raise osv.except_osv(_('Error !'), _('Please define sequence on journal !'))
            
            ref = False
            if inv.type in ('purchase', 'receipt'):
                ref = inv.reference
            else:
                ref = invoice_pool._convert_ref(cr, uid, name)
            
            company_currency = inv.company_id.currency_id.id
            diff_currency_p = inv.currency_id.id <> company_currency

            move = {
                'name' : name,
                'journal_id': journal.id,
                'type' : inv.type,
                'narration' : inv.narration and inv.narration or inv.name,
                'date':inv.date,
                'ref':ref
            }
            
            if inv.period_id:
                move.update({
                    'period_id': inv.period_id.id
                })
            
            move_id = move_pool.create(cr, uid, move)

            #create the first line manually
            move_line = {
                'name':inv.name and inv.name or '/',
                'debit':False,
                'credit':False,
                'account_id':inv.account_id.id,
                'move_id':move_id ,
                'journal_id':inv.journal_id.id,
                'period_id':inv.period_id.id,
                'partner_id':inv.partner_id.id,
                'ref':ref,
                'date':inv.date
            }
            
            if diff_currency_p:
                amount_currency = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.amount)
                inv.amount = amount_currency
                move_line.update({
                    'amount_currency':amount_currency,
                    'currency_id':inv.currency_id.id
                })

            if inv.type in ('sale', 'receipt'):
                move_line.update({
                    'debit':inv.amount
                })
            elif inv.type == 'purchase':
                move_line.update({
                    'credit':inv.amount
                })            

            line_ids = []
            line_ids += [move_line_pool.create(cr, uid, move_line)]

            for line in inv.payment_ids:
                rec_ids = []
                amount=0.0

                if inv.type in ('payment'):
                    ref = line.ref
                
                move_line = {
                     'name':line.name and line.name or '/',
                     'debit':False,
                     'credit':False,
                     'account_id':line.account_id.id or False,
                     'move_id':move_id ,
                     'journal_id':inv.journal_id.id,
                     'period_id':inv.period_id.id,
                     'partner_id':line.partner_id.id or False,
                     'ref':ref,
                     'date':inv.date,
                     'analytic_account_id':False
                }
                
                if diff_currency_p:
                    amount_currency = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, line.amount)
                    line.amount = amount_currency
                    move_line.update({
                        'amount_currency':amount_currency,
                        'currency_id':inv.currency_id.id
                    })
                
                if line.account_analytic_id:
                    move_line.update({
                        'analytic_account_id':line.account_analytic_id.id
                    })

                if inv.type in ('sale', 'receipt'):
                    move_line.update({
                        'credit': line.amount or False
                    })

                if inv.type in ('purchase'):
                    move_line.update({
                        'debit': line.amount or False
                    })

                move_line_id = move_line_pool.create(cr, uid, move_line)
                line_ids += [move_line_id]

                if inv.type in ('payment', 'receipt') and line.move_id:
                    rec_ids += [move_line_id]
#                    for move_line in line.move_id.line_id:
#                        if line.account_id.id == move_line.account_id.id:
                    if line.move_line_id:
                        rec_ids += [line.move_line_id.id]
                        
                    if rec_ids:
                        cr.commit()
                        move_line_pool.reconcile_partial(cr, uid, rec_ids)

            if inv.type in ('sale', 'purchase') and inv.tax_amount > 0:
                name = '/'
                if not inv.tax_id:
                    name = inv.tax_id.name
                move_line = {
                    'name':name,
                    'account_id':False,
                    'move_id':move_id ,
                    'journal_id':inv.journal_id.id,
                    'period_id':inv.period_id.id,
                    'partner_id':inv.partner_id.id,
                    'ref':ref,
                    'date':inv.date
                }
                account_id = False
                if inv.tax_id and inv.tax_id.account_collected_id:
                    account_id = inv.tax_id.account_collected_id.id
                    
                if inv.type == 'sale':
                    move_line.update({
                        'credit':inv.tax_amount,
                        'account_id':account_id and account_id or inv.journal_id.default_credit_account_id.id
                    })

                elif inv.type == 'purchase':
                    move_line.update({
                        'debit':inv.tax_amount,
                        'account_id':account_id and account_id or inv.journal_id.default_debit_account_id.id
                    })

                move_line_id = move_line_pool.create(cr, uid, move_line)
                line_ids += [move_line_id]
            
            rec = {
                'move_id': move_id
            }
            
            message = _('Voucher ') + " '" + inv.name + "' "+ _("is confirm")
            self.log(cr, uid, inv.id, message)
            
            self.write(cr, uid, [inv.id], rec)
            move_pool.post(cr, uid, [move_id], context={})
            
        return True

    def _convert_ref(self, cr, uid, ref):
        return (ref or '').replace('/','')

    def copy(self, cr, uid, id, default={}, context=None):
        res = {
            'state':'draft',
            'number':False,
            'move_id':False
        }
        default.update(res)
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(account_voucher, self).copy(cr, uid, id, default, context)
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Returns views and fields for current model where view will depend on {view_type}.
        @param cr: A database cursor
        @param user: ID of the user currently logged in
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
    _description = 'Voucher Line'

    _columns = {
        'voucher_id':fields.many2one('account.voucher', 'Voucher'),
        'name':fields.char('Description', size=256, required=True),
        'account_id':fields.many2one('account.account','Account', required=True, domain=[('type','<>','view')]),
        'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
        'amount':fields.float('Amount'),
#        'type':fields.selection([('dr','Debit'),('cr','Credit')], 'Cr/Dr'),
        'ref':fields.char('Reference', size=32),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account'),
        'stype':fields.selection([('service','Service'),('other','Other')], 'Product Type'),
        'move_line_id': fields.many2one('account.move.line', 'Journal Item'),
        'date_original': fields.related('move_line_id','date', type='date', relation='account.move.line', string='Date', readonly="1"),
#        'date_original': fields.date('Date', readonly="1"), #fields.related account.move.line
        'date_due': fields.related('move_line_id','date_maturity', type='date', relation='account.move.line', string='Due Date', readonly="1"),
#        'date_due': fields.date('Due Date', readonly="1"), #fields.related account.move.line
        'amount_original': fields.float('Originial Amount', readonly="1"), #fields.related account.move.line
        'amount_unreconciled': fields.related('move_line_id','balance', type='float', relation='account.move.line', string='Open Balance', readonly="1"),
#        'amount_unreconciled': fields.float('Open Balance', readonly="1"), #fields.related account.move.line
        'move_id' : fields.many2one('account.move','Bill / Invoice'),
    }
    _defaults = {
        'name': lambda *a: '/'
    }

#    def create(self, cr, user, vals, context={}):
#        """
#        Create a new record for a model account_voucher_line
#        @param cr: A database cursor
#        @param user: ID of the user currently logged in
#        @param vals: provides data for new record
#        @param context: context arguments, like lang, time zone
#        
#        @return: Returns an id of the new record
#        """
#        if vals.get('account_id')
#        res_id = super(account_voucher_line, self).create(cr, user, vals, context)
#        return res_id

    def onchange_move_line_id(self, cr, user, ids, move_line_id, context={}):
        """
        Returns a dict that contains new values and context

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        
        @return: Returns a dict which contains new values, and context
        """
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id)

            move_id = move_line.move_id.id
            amount = move_line.credit and move_line.credit or move_line.debit
            account_id = move_line.account_id.id

            res.update({
                'move_id':move_id,
                'amount':amount,
                'account_id':account_id
            })
            context.update({
                'journal_id':move_line.journal_id.id,
                'partner_id':move_line.partner_id.id,
                'account_id':account_id
            })
        return {
            'value':res,
            'context':context,
        }
    
    def default_get(self, cr, user, fields_list, context=None):
        """
        Returns default values for fields
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param fields_list: list of fields, for which default values are required to be read 
        @param context: context arguments, like lang, time zone
        
        @return: Returns a dict that contains default values for fields
        """
        journal_pool = self.pool.get('account.journal')
        partner_pool = self.pool.get('res.partner')
        account_id = False

        values = super(account_voucher_line, self).default_get(cr, user, fields_list, context=context)
        journal_id = context.get('journal_id', False)
        ttype = context.get('type', False)
        partner_id = context.get('partner_id', False)
        
        if ttype and journal_id and ttype in ('sale', 'purchase'):
            journal = journal_pool.browse(cr, user, journal_id)
            if ttype == 'sale' and journal:
                account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            elif ttype == 'purchase' and journal:
                account_id = journal.default_credit_account_id and journal.default_debit_account_id.id or False
        elif  ttype and partner_id and ttype in ('payment', 'receipt'):
            partner = partner_pool.browse(cr, user, partner_id)
            if ttype == 'receipt' and partner:
                account_id = partner.property_account_receivable and partner.property_account_receivable.id or False
            elif ttype == 'payment' and partner:
                account_id = partner.property_account_receivable and partner.property_account_payable.id or False

        if not account_id:
            raise osv.except_osv(_('Invalid Error !'), _('Please change partner and try again !'))
        values.update({
            'account_id':account_id
        })
        return values
account_voucher_line()

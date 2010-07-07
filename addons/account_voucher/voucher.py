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
from osv import fields
from osv import osv

journal2type = {
    'cash':'rec_voucher',
    'bank':'bank_rec_voucher',
    'cash':'pay_voucher',
    'sale':'journal_sale_vou',
    'purchase':'journal_pur_voucher',
    'general':'journal_voucher'
}

type2journal = {
    'rec_voucher': 'cash',
    'bank_rec_voucher': 'bank',
    'pay_voucher': 'cash',
    'bank_pay_voucher': 'bank',
    'cont_voucher': 'cash',
    'journal_sale_vou': 'sale',
    'journal_pur_voucher': 'purchase',
    'journal_voucher':'general'
}

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
        'max_amount': fields.float('Verify Transaction', digits=(16, 2), help="Validate voucher entry twice before posting it, if transection amount more then entered here"),
    }
account_journal()

class account_voucher(osv.osv):

    def _get_period(self, cr, uid, context={}):
        if context.get('period_id', False):
            return context.get('period_id')

        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    def _get_type(self, cr, uid, context={}):
        vtype = context.get('type', 'bank')
        voucher_type = journal2type.get(vtype)
        return voucher_type

    def _get_reference_type(self, cursor, user, context=None):
        return [('none', 'Free Reference')]

    def _get_journal(self, cr, uid, context={}):
        journal_pool = self.pool.get('account.journal')

        if context.get('journal_id', False):
            return context.get('journal_id')

        type_inv = context.get('type', 'rec_voucher')

        ttype = type2journal.get(type_inv, type_inv)
        res = journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)

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
    _order = "date desc"
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([
            ('pay_voucher','Cash Payment'),
            ('bank_pay_voucher','Bank Payment'),
            ('rec_voucher','Cash Receipt'),
            ('bank_rec_voucher','Bank Receipt'),
#            ('cont_voucher','Contra'),
            ('journal_sale_vou','Journal Sale'),
            ('journal_pur_voucher','Journal Purchase'),
            ('journal_voucher','Journal Voucher'),
            ],'Entry Type', select=True , size=128, readonly=True, states={'draft':[('readonly',False)]}),
        'date':fields.date('Date', readonly=True, states={'draft':[('readonly',False)]}),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}, domain=[('type','<>','view')]),
        'payment_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=False, states={'proforma':[('readonly',True)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'posted':[('readonly',True)]}),
        'narration':fields.text('Narration', readonly=True, states={'draft':[('readonly',False)]}, required=False),
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
        'amount':fields.float('Amount', readonly=True),
        'reference': fields.char('Voucher Reference', size=64),
        'reference_type': fields.selection(_get_reference_type, 'Reference Type',
            required=True),
        'number': fields.related('move_id', 'name', type="char", readonly=True, string='Number'),
        'move_id':fields.many2one('account.move', 'Account Entry'),
        'move_ids':fields.many2many('account.move.line', 'voucher_id', 'account_id', 'rel_account_move', 'Real Entry'),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]})
    }

    _defaults = {
        'period_id': _get_period,
        'type': _get_type,
        'journal_id':_get_journal,
        'currency_id': _get_currency,
        'state': lambda *a: 'draft',
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
        'reference_type': lambda *a: "none",
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
    }

    def onchange_account(self, cr, uid, ids, account_id):
        if not account_id:
            return {
                'value':{'amount':False}
            }
        account = self.pool.get('account.account').browse(cr, uid, account_id)
        balance=account.balance
        return {
            'value':{'amount':balance}
        }

    def onchange_journal(self, cr, uid, ids, journal_id, type):
        if not journal_id:
            return {
                'value':{'account_id':False}
            }
        journal = self.pool.get('account.journal')

        if journal_id and (type in ('rec_voucher','bank_rec_voucher','journal_pur_voucher','journal_voucher')):
            account_id = journal.browse(cr, uid, journal_id).default_debit_account_id
            return {
                'value':{'account_id':account_id.id}
            }
        elif journal_id and (type in ('pay_voucher','bank_pay_voucher','journal_sale_vou')) :
                account_id = journal.browse(cr, uid, journal_id).default_credit_account_id
                return {
                    'value':{'account_id':account_id.id}
                }
        else:
            account_id = journal.browse(cr, uid, journal_id).default_credit_account_id
            return {
                'value':{'account_id':account_id.id}
            }

    def open_voucher(self, cr, uid, ids, context={}):
        voucher = self.pool.get('account.voucher').browse(cr, uid, ids)[0]
        total = 0
        for line in voucher.payment_ids:
            total += line.amount
        
        if total != 0:
            res = {
                'amount':total, 
                'state':'proforma'
            }
            self.write(cr, uid, ids, res)
        else:
            raise osv.except_osv('Invalid action !', 'You cannot post to Pro-Forma a voucher with Total amount = 0 !')
        return True

    def proforma_voucher(self, cr, uid, ids, context={}):
        self.action_move_line_create(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'posted'})
        return True

    def cancel_voucher(self, cr, uid, ids, context={}):
        move_pool = self.pool.get('account.move')
        
        for voucher in self.browse(cr, uid, ids):
            if voucher.move_id:
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
                move_pool.unlink(cr, uid, [voucher.move_id.id])
        
        res = {
            'state':'cancel', 
            'move_id':False,
            'move_ids':[(6, 0,[])]
        }
        self.write(cr, uid, ids, res)
        return True

    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft'})
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

    def action_move_line_create(self, cr, uid, ids, *args):

        journal_pool = self.pool.get('account.journal')
        sequence_pool = self.pool.get('ir.sequence')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        analytic_pool = self.pool.get('account.analytic.line')
        currency_pool = self.pool.get('res.currency')
        
        for inv in self.browse(cr, uid, ids):

            if inv.move_id:
                continue
            
            company_currency = inv.company_id.currency_id.id
            diff_currency_p = inv.currency_id.id <> company_currency
            ref = inv.reference
            
            journal = journal_pool.browse(cr, uid, inv.journal_id.id)
            if journal.sequence_id:
                name = sequence_pool.get_id(cr, uid, journal.sequence_id.id)
            
            move = {
                'name' : name,
                'journal_id': journal.id,
                'type' : inv.type,
                'narration' : inv.narration and inv.narration or inv.name,
                'date':inv.date
            }
            
            if inv.period_id:
                move.update({
                    'period_id': inv.period_id.id
                })
            
            move_id = move_pool.create(cr, uid, move)
            
            #create the first line manually
            move_line = {
                'name': inv.name,
                'debit': False,
                'credit':False,
                'account_id': inv.account_id.id or False,
                'move_id': move_id ,
                'journal_id': inv.journal_id.id,
                'period_id': inv.period_id.id,
                'partner_id': False,
                'ref': ref,
                'date': inv.date
            }
            if diff_currency_p:
                amount_currency = currency_pool.compute(cr, uid, inv.currency_id.id, company_currency, inv.amount)
                inv.amount = amount_currency
                move_line.update({
                    'amount_currency':amount_currency,
                    'currency_id':inv.currency_id.id
                })
            
            if inv.type in ('rec_voucher', 'bank_rec_voucher', 'journal_pur_voucher', 'journal_voucher'):
                move_line['debit'] = inv.amount
            else:
                move_line['credit'] = inv.amount
            
            line_ids = []
            line_ids += [move_line_pool.create(cr, uid, move_line)]
            for line in inv.payment_ids:
                amount=0.0
                move_line = {
                     'name': line.name,
                     'debit': False,
                     'credit': False,
                     'account_id': line.account_id.id or False,
                     'move_id': move_id ,
                     'journal_id': inv.journal_id.id,
                     'period_id': inv.period_id.id,
                     'partner_id': line.partner_id.id or False,
                     'ref': ref,
                     'date': inv.date,
                     'analytic_account_id': False
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
                
                if line.type == 'dr':
                    move_line.update({
                        'debit': line.amount or False
                    })
                    amount = line.amount
                    
                elif line.type == 'cr':
                    move_line.update({
                        'credit': line.amount or False
                    })
                    amount = line.amount * (-1)

                move_line_id = move_line_pool.create(cr, uid, move_line)
                line_ids += [move_line_id]
            
            rec = {
                'move_id': move_id,
                'move_ids':[(6, 0,line_ids)]
            }
            self.write(cr, uid, [inv.id], rec)
            
        return True

    def _convert_ref(self, cr, uid, ref):
        return (ref or '').replace('/','')

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        types = {
            'pay_voucher': 'CPV: ',
            'rec_voucher': 'CRV: ',
            'cont_voucher': 'CV: ',
            'bank_pay_voucher': 'BPV: ',
            'bank_rec_voucher': 'BRV: ',
            'journal_sale_vou': 'JSV: ',
            'journal_pur_voucher': 'JPV: ',
            'journal_voucher':'JV'
        }
        return [(r['id'], types[r['type']]+(r['number'] or '')+' '+(r['name'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'name'], context, load='_classic_write')]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if name:
            ids = self.search(cr, user, [('number','=',name)]+ args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'state':'draft', 'number':False, 'move_id':False, 'move_ids':False, 'payment_ids':False})
        if 'date' not in default:
            default['date'] = time.strftime('%Y-%m-%d')
        return super(account_voucher, self).copy(cr, uid, id, default, context)

account_voucher()

class account_voucher_line(osv.osv):
    _name = 'account.voucher.line'
    _description = 'Voucher Line'
    _columns = {
        'voucher_id':fields.many2one('account.voucher', 'Voucher'),
        'name':fields.char('Description', size=256, required=True),
        'account_id':fields.many2one('account.account','Account', required=True, domain=[('type','<>','view')]),
        'partner_id': fields.many2one('res.partner', 'Partner', change_default=True),
        'amount':fields.float('Amount'),
        'type':fields.selection([('dr','Debit'),('cr','Credit')], 'Type'),
        'ref':fields.char('Reference', size=32),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Analytic Account')
    }
    _defaults = {
        'type': lambda *a: 'cr'
    }

    def move_line_get(self, cr, uid, voucher_id, context={}):
        res = []

        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.voucher').browse(cr, uid, voucher_id)
        company_currency = inv.company_id.currency_id.id
        cur = inv.currency_id

        for line in inv.payment_ids:
            res.append(self.move_line_get_item(cr, uid, line, context))
        return res

    def onchange_partner(self, cr, uid, ids, partner_id, ttype ,type1):
        if not partner_id:
            return {'value' : {'account_id' : False, 'type' : False ,'amount':False}}
        obj = self.pool.get('res.partner')
        account_id = False
        if type1 in ('rec_voucher','bank_rec_voucher', 'journal_voucher'):
            account_id = obj.browse(cr, uid, partner_id).property_account_receivable
            balance = obj.browse(cr,uid,partner_id).credit
            ttype = 'cr'
        elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') :
            account_id = obj.browse(cr, uid, partner_id).property_account_payable
            balance = obj.browse(cr,uid,partner_id).debit
            ttype = 'dr'
        elif type1 in ('journal_sale_vou') :
            account_id = obj.browse(cr, uid, partner_id).property_account_receivable
            balance = obj.browse(cr,uid,partner_id).credit
            ttype = 'dr'
        elif type1 in ('journal_pur_voucher') :
            account_id = obj.browse(cr, uid, partner_id).property_account_payable
            balance = obj.browse(cr,uid,partner_id).debit
            ttype = 'cr'

        return {
            'value' : {'account_id' : account_id.id, 'type' : ttype, 'amount':balance}
        }

    def onchange_amount(self, cr, uid, ids, partner_id, amount, type, type1):
        if not amount:
            return {'value' : {}}
        if partner_id:
            obj = self.pool.get('res.partner')
            if type1 in ('rec_voucher', 'bank_rec_voucher', 'journal_voucher'):
                if amount < 0 :
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    type = 'dr'
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    type = 'cr'

            elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') :
                if amount < 0 :
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    type = 'cr'
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    type = 'dr'

            elif type1 in ('journal_sale_vou') :
                if amount < 0 :
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    type = 'cr'
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    type = 'dr'

            elif type1 in ('journal_pur_voucher') :
                if amount< 0 :
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    type = 'dr'
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    type = 'cr'
        else:
            if type1 in ('rec_voucher', 'bank_rec_voucher', 'journal_voucher'):
                if amount < 0 :
                    type = 'dr'
                else:
                    type = 'cr'
            elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') :
                if amount < 0 :
                    type = 'cr'
                else:
                    type = 'dr'
            elif type1 in ('journal_sale_vou') :
                if amount < 0 :
                    type = 'cr'
                else:
                    type = 'dr'
            elif type1 in ('journal_pur_voucher') :
                if amount< 0 :
                    type = 'dr'
                else:
                    type = 'cr'

        return {
            'value' : { 'type' : type , 'amount':amount}
        }

    def onchange_type(self, cr, uid, ids, partner_id, amount, type, type1):
        if partner_id:
            obj = self.pool.get('res.partner')
            if type1 in ('rec_voucher','bank_rec_voucher', 'journal_voucher'):
                if type == 'dr' :
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    total=amount*(-1)
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    total=amount*(-1)

            elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') :
                if type == 'cr' :
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    total=amount*(-1)
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    total=amount*(-1)

            elif type1 in ('journal_sale_vou') :
                if type == 'cr' :
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    total=amount*(-1)
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    total=amount*(-1)
            elif type1 in ('journal_pur_voucher') :
                if type == 'dr' :
                    account_id = obj.browse(cr, uid, partner_id).property_account_receivable
                    total=amount*(-1)
                else:
                    account_id = obj.browse(cr, uid, partner_id).property_account_payable
                    total=amount*(-1)
        else:
            if type1 in ('rec_voucher','bank_rec_voucher', 'journal_voucher'):
                if type == 'dr' :
                    total=amount*(-1)
                else:
                    total=amount*(-1)

            elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') :
                if type == 'cr' :
                    total=amount*(-1)
                else:
                    total=amount*(-1)

            elif type1 in ('journal_sale_vou') :
                if type == 'cr' :
                    total=amount*(-1)
                else:
                    total=amount*(-1)
            elif type1 in ('journal_pur_voucher') :
                if type == 'dr' :
                    total=amount*(-1)
                else:
                    total=amount*(-1)

        return {
            'value' : {'type' : type , 'amount':total}
        }

    def move_line_get_item(self, cr, uid, line, context={}):
        return {
            'type':'src',
            'name': line.name[:64],
            'amount':line.amount,
            'account_id':line.account_id.id,
            'partner_id':line.partner_id.id or False ,
            'account_analytic_id':line.account_analytic_id.id or False,
            'ref' : line.ref
        }

account_voucher_line()

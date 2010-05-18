# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import netsvc
from osv import fields, osv
import ir
import pooler
import mx.DateTime
from mx.DateTime import RelativeDateTime
from tools import config

class ir_sequence_type(osv.osv):
    _inherit = "ir.sequence.type"
    _columns = {
        'name': fields.char('Sequence Name',size=128, required=True),
        'code': fields.char('Sequence Code',size=128, required=True),
    }
ir_sequence_type()

class account_voucher(osv.osv):
    def _get_period(self, cr, uid, context):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False
        
    def _get_type(self, cr, uid, context={}):
        type = context.get('type', 'rec_voucher')
        return type
    
    def _get_reference_type(self, cursor, user, context=None):
        return [('none', 'Free Reference')]
    
    def _get_journal(self, cr, uid, context):
        type_inv = 'rec_voucher'
        
        if type(context) == type(''):
            type_inv = context
        elif type(context) == type({}):
            type_inv = context.get('type', 'rec_voucher')

        type2journal = {
            'rec_voucher': 'cash', 
            'bank_rec_voucher': 'cash',
            'pay_voucher': 'cash',
            'bank_pay_voucher': 'cash', 
            'cont_voucher': 'cash',
            'journal_sale_vou': 'sale',
            'journal_pur_voucher': 'purchase',
            'journal_voucher':'expanse'
        }
        
        journal_obj = self.pool.get('account.journal')
        ttype = type2journal.get(type_inv, 'cash')
        res = journal_obj.search(cr, uid, [('type', '=', ttype)], limit=1)
        
        if res:
            return res[0]
        else:
            return False
        
    def _get_currency(self, cr, uid, context):
        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, [uid])[0]
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return pooler.get_pool(cr.dbname).get('res.currency').search(cr, uid, [('rate','=',1.0)])[0]
        
    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _order = "number"
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([
            ('pay_voucher','Cash Payment Voucher'),
            ('bank_pay_voucher','Bank Payment Voucher'),
            ('rec_voucher','Cash Receipt Voucher'),
            ('bank_rec_voucher','Bank Receipt Voucher'),
            ('cont_voucher','Contra Voucher'),
            ('journal_sale_vou','Journal Sale Voucher'),
            ('journal_pur_voucher','Journal Purchase Voucher'),
            ('journal_voucher','Journal Voucher'),
            ],'Type', readonly=True, select=True , size=128),
        'date':fields.date('Date', readonly=True, states={'draft':[('readonly',False)]}),
        'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'account_id':fields.many2one('account.account', 'Account', required=True, readonly=True, states={'draft':[('readonly',False)]}, domain=[('type','<>','view')]),
        'payment_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=False, states={'proforma':[('readonly',True)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),
        'narration':fields.text('Narration', readonly=True, states={'draft':[('readonly',False)]}, required=True),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'state':fields.selection(
                    [('draft','Draft'),
                     ('proforma','Pro-forma'),
                     ('posted','Posted'),
                     ('cancel','Cancel')
                    ], 'State', 
                    readonly=True),
        'amount':fields.float('Amount', readonly=True),
        'number':fields.char('Number', size=32, readonly=True),
        'reference': fields.char('Voucher Reference', size=64),
        'reference_type': fields.selection(_get_reference_type, 'Reference Type',
            required=True),
        'move_id':fields.many2one('account.move', 'Account Entry'),
        'move_ids':fields.many2many('account.move.line', 'voucher_id', 'account_id', 'rel_account_move', 'Real Entry'),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True, states={'draft':[('readonly',False)]})
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
        'date' : lambda *a: time.strftime('%Y-%m-%d'),
        'period_id': _get_period,
        'type': _get_type,
        'reference_type': lambda *a: 'none',
        'journal_id':_get_journal,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'currency_id': _get_currency,
    }
    
    def _get_analityc_lines(self, cr, uid, id):
        inv = self.browse(cr, uid, [id])[0]
        cur_obj = self.pool.get('res.currency')
        
    def onchange_account(self, cr, uid, ids, account_id):
        if not account_id:
            return {'value':{'amount':False}}
        account = self.pool.get('account.account').browse(cr,uid,account_id)
        balance=account.balance
        return {'value':{'amount':balance}}

    def onchange_journal(self, cr, uid, ids, journal_id,type):
        if not journal_id:
            return {'value':{'account_id':False}}
        journal = self.pool.get('account.journal')
        if journal_id and (type in ('rec_voucher','bank_rec_voucher','journal_pur_voucher','journal_voucher')):
            account_id = journal.browse(cr, uid, journal_id).default_debit_account_id
            return {'value':{'account_id':account_id.id}}
        elif journal_id and (type in ('pay_voucher','bank_pay_voucher','journal_sale_vou')) :
                account_id = journal.browse(cr, uid, journal_id).default_credit_account_id
                return {'value':{'account_id':account_id.id}}
        else:
            account_id = journal.browse(cr, uid, journal_id).default_credit_account_id
            return {'value':{'account_id':account_id.id}}
        
    def open_voucher(self, cr, uid, ids, context={}):
        obj=self.pool.get('account.voucher').browse(cr,uid,ids)
        total=0
        for i in obj[0].payment_ids:
            total+=i.amount
        if total!=0:
            self.write(cr,uid,ids,{'amount':total})
            self.write(cr, uid, ids, {'state':'proforma'})
        else:
            raise osv.except_osv('Invalid action !', 'You can not post to Pro-Forma a voucher with Total amount = 0')
        return True
    
    def proforma_voucher(self, cr, uid, ids, context={}):
        self.action_number(cr, uid, ids)
        self.action_move_line_create(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'posted'})
        return True
    
    def cancel_voucher(self,cr,uid,ids,context={}):
        self.action_cancel(cr, uid, ids)
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
        
    def action_cancel_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def unlink(self, cr, uid, ids, context={}):
        vouchers = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in vouchers:
            if t['state'] in ('draft', 'cancel'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv('Invalid action !', 'Cannot delete Voucher(s) which are already opened or paid !')
        osv.osv.unlink(self, cr, uid, unlink_ids)
        return True
         
    def _get_analytic_lines(self, cr, uid, id):
        inv = self.browse(cr, uid, [id])[0]
        cur_obj = self.pool.get('res.currency')

        company_currency = inv.company_id.currency_id.id
        if inv.type in ('rec_voucher'):
            sign = 1
        else:
            sign = -1

        iml = self.pool.get('account.voucher.line').move_line_get(cr, uid, inv.id)
        
        for il in iml:
            if il['account_analytic_id']:
                if inv.type in ('pay_voucher', 'rec_voucher','cont_voucher','bank_pay_voucher','bank_rec_voucher','journal_sale_vou','journal_pur_voucher'):
                    ref = inv.reference
                else:
                    ref = self._convert_ref(cr, uid, inv.number)
                    
                il['analytic_lines'] = [(0, 0, {
                    'name': il['name'],
                    'date': inv['date'],
                    'account_id': il['account_analytic_id'],
                    'amount': inv['amount'] * sign,
                    'general_account_id': il['account_id'] or False,
                    'journal_id': self.pool.get('account.voucher').browse(cr, uid, id).journal_id.analytic_journal_id.id or False,
                    'ref': ref,
                })]
        return iml
    
    def action_move_line_create(self, cr, uid, ids, *args):
        for inv in self.browse(cr, uid, ids):
            if inv.move_id:
                continue
            company_currency = inv.company_id.currency_id.id

            line_ids = self.read(cr, uid, [inv.id], ['payment_ids'])[0]['payment_ids']
            ils = self.pool.get('account.voucher.line').read(cr, uid, line_ids)

            iml = self._get_analytic_lines(cr, uid, inv.id)

            diff_currency_p = inv.currency_id.id <> company_currency

            total = 0
            if inv.type in ('pay_voucher', 'journal_voucher', 'rec_voucher','cont_voucher','bank_pay_voucher','bank_rec_voucher','journal_sale_vou','journal_pur_voucher'):
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                
            date = inv.date
            total_currency = 0
            acc_id = None
            for i in iml:
                partner_id=i['partner_id']
                acc_id = i['account_id']    
                if inv.currency_id.id != company_currency:
                    i['currency_id'] = inv.currency_id.id
                    i['amount_currency'] = i['amount']
                else:
                    i['amount_currency'] = False
                    i['currency_id'] = False
                if inv.type in ('rec_voucher','bank_rec_voucher','journal_pur_voucher','journal_voucher'):
                    total += i['amount']
                    total_currency += i['amount_currency'] or i['amount']
                    i['amount'] = - i['amount']
                else:
                    total -= i['amount']
                    total_currency -= i['amount_currency'] or i['amount']

            name = inv['name'] or '/'
            totlines = False

            iml.append({
                'type': 'dest',
                'name': name,
                'amount': total or False,
                'account_id': acc_id,
                'amount_currency': diff_currency_p \
                        and total_currency or False,
                'currency_id': diff_currency_p \
                        and inv.currency_id.id or False,
                'ref': ref,
                'partner_id':partner_id or False,
            })

            date = inv.date
            inv.amount=total

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x,date, context={})) ,iml)
            an_journal_id=inv.journal_id.analytic_journal_id.id
            journal_id = inv.journal_id.id
            
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
            if journal.sequence_id:
                name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)

            move = {
                'name' : name, 
                'journal_id': journal_id, 
                'type' : inv.type,
                'narration' : inv.narration
            }
            if inv.period_id:
                move['period_id'] = inv.period_id.id
                for i in line:
                    i[2]['period_id'] = inv.period_id.id
            move_id = self.pool.get('account.move').create(cr, uid, move)
            ref = move['name']
            amount=0.0
            
            #create the first line our self
            move_line = {
                'name': inv.name,
                'debit': False,
                'credit':False,
                'account_id': inv.account_id.id or False,
                'move_id':move_id ,
                'journal_id':journal_id ,
                'period_id':inv.period_id.id,
                'partner_id': False,
                'ref': ref, 
                'date': inv.date
            }
            if inv.type in ('rec_voucher', 'bank_rec_voucher', 'journal_pur_voucher', 'journal_voucher'):
                move_line['debit'] = inv.amount
            else:
                move_line['credit'] = inv.amount * (-1)
            self.pool.get('account.move.line').create(cr, uid, move_line)
            
            for line in inv.payment_ids:
                
                move_line = {
                    'name':line.name,
                     'debit':False,
                     'credit':False,
                     'account_id':line.account_id.id or False,
                     'move_id':move_id ,
                     'journal_id':journal_id ,
                     'period_id':inv.period_id.id,
                     'partner_id':line.partner_id.id or False,
                     'ref':ref, 
                     'date':inv.date
                 }
                
                if line.type == 'dr':
                    move_line['debit'] = line.amount or False
                    amount=line.amount
                elif line.type == 'cr':
                    move_line['credit'] = line.amount or False
                    amount=line.amount * (-1)
                
                ml_id=self.pool.get('account.move.line').create(cr, uid, move_line)
                
                if inv.narration:
                    line.name=inv.narration
                else:
                    line.name=line.name
                
                if line.account_analytic_id:
                    an_line = {
                         'name':line.name,
                         'date':inv.date,
                         'amount':amount,
                         'account_id':line.account_analytic_id.id or False,
                         'move_id':ml_id,
                         'journal_id':an_journal_id ,
                         'general_account_id':line.account_id.id,
                         'ref':ref
                     }
                    self.pool.get('account.analytic.line').create(cr,uid,an_line)
                
            self.write(cr, uid, [inv.id], {'move_id': move_id})
            obj=self.pool.get('account.move').browse(cr, uid, move_id)
            
            for line in obj.line_id :
                cr.execute('insert into voucher_id (account_id,rel_account_move) values (%d, %d)',(int(ids[0]),int(line.id)))
                
        return True

    
    def line_get_convert(self, cr, uid, x, date, context={}):
       
        return {
            'date':date,
            'date_maturity': x.get('date_maturity', False),
            'partner_id':x.get('partner_id',False),
            'name':x['name'][:64],
            'debit':x['amount']>0 and x['amount'],
            'credit':x['amount']<0 and -x['amount'],
            'account_id':x['account_id'],
            'analytic_lines':x.get('analytic_lines', []),
            'amount_currency':x.get('amount_currency', False),
            'currency_id':x.get('currency_id', False),
            'tax_code_id': x.get('tax_code_id', False),
            'tax_amount': x.get('tax_amount', False),
            'ref':x.get('ref',False)
        }
    def _convert_ref(self, cr, uid, ref):
        return (ref or '').replace('/','')
    
    
    def action_number(self, cr, uid, ids, *args):
        cr.execute('SELECT id, type, number, move_id, reference ' \
                'FROM account_voucher ' \
                'WHERE id IN %s',
                   (tuple(ids),))
        for (id, invtype, number, move_id, reference) in cr.fetchall():
            if not number:
                number = self.pool.get('ir.sequence').get(cr, uid, invtype)

                if type in ('pay_voucher', 'journal_voucher', 'rec_voucher','cont_voucher','bank_pay_voucher','bank_rec_voucher','journal_sale_vou','journal_pur_voucher'):
                    ref = reference
                else:
                    ref = self._convert_ref(cr, uid, number)
                    
                cr.execute('UPDATE account_voucher SET number=%s ' \
                        'WHERE id=%d', (number, id))
                cr.execute('UPDATE account_move_line SET ref=%s ' \
                        'WHERE move_id=%d AND (ref is null OR ref = \'\')',
                        (ref, move_id))
                cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                        'FROM account_move_line ' \
                        'WHERE account_move_line.move_id = %d ' \
                            'AND account_analytic_line.move_id = account_move_line.id',
                            (ref, move_id))
        return True


    
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

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
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
    
    def action_cancel(self, cr, uid, ids, *args):
        account_move_obj = self.pool.get('account.move')
        voucher = self.read(cr, uid, ids, ['move_id'])
        for i in voucher:
            if i['move_id']:
                account_move_obj.button_cancel(cr, uid, [i['move_id'][0]])
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                account_move_obj.unlink(cr, uid, [i['move_id'][0]])
        self.write(cr, uid, ids, {'state':'cancel', 'move_id':False})
        return True
    
account_voucher()

class VoucherLine(osv.osv):
    _name = 'account.voucher.line'
    _description = 'Voucher Line'
    _columns = {
        'voucher_id':fields.many2one('account.voucher', 'Voucher'),
        'name':fields.char('Description', size=256, required=True),
        'account_id':fields.many2one('account.account','Account', required=True, domain=[('type','<>','view')]),
        'partner_id': fields.many2one('res.partner', 'Partner', change_default=True),
        'amount':fields.float('Amount'),
        'type':fields.selection([('dr','Debit'),('cr','Credit')], 'Type'),
        'ref':fields.char('Ref.', size=32),
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
        
    def onchange_amount(self, cr, uid, ids,partner_id,amount, type,type1):
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
        
    def onchange_type(self, cr, uid, ids,partner_id,amount,type,type1):
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
        
VoucherLine()







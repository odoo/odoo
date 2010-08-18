# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from tools.translate import _

#class account_move_line(osv.osv):
#    _inherit = "account.move.line"
#    _columns = {
#        'voucher_invoice': fields.many2one('account.invoice', 'Invoice', readonly=True),
#    }
#account_move_line()

class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    
    _columns = {
        'payment_ids':fields.one2many('account.voucher.line', 'voucher_id', 'Voucher Lines', readonly=True, states={'draft':[('readonly',False)]}),
    }

    def action_move_line_create(self, cr, uid, ids, *args):

        journal_pool = self.pool.get('account.journal')
        sequence_pool = self.pool.get('ir.sequence')
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        analytic_pool = self.pool.get('account.analytic.line')
        currency_pool = self.pool.get('res.currency')
        invoice_pool = self.pool.get('account.invoice')
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
                'name':inv.name,
                'debit':False,
                'credit':False,
                'account_id':inv.account_id.id or False,
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
            
            if inv.type in ('receipt', 'purchase'):
                move_line['debit'] = inv.amount
            else:
                move_line['credit'] = inv.amount
            
            line_ids = []
            line_ids += [move_line_pool.create(cr, uid, move_line)]
            rec_ids = []
            
            if inv.type == 'sale' and inv.pay_now == 'pay_now':
                #create the payment line manually
                move_line = {
                    'name':inv.name,
                    'debit':inv.pay_amount,
                    'credit':False,
                    'account_id':inv.pay_account_id.id or False,
                    'move_id':move_id ,
                    'journal_id':inv.pay_journal_id.id,
                    'period_id':inv.period_id.id,
                    'partner_id':inv.partner_id.id,
                    'ref':ref,
                    'date':inv.date
                }
                line_ids += [move_line_pool.create(cr, uid, move_line)]
            else:
                for line in inv.payment_ids:
                    amount=0.0

                    if inv.type in ('payment'):
                        ref = line.ref
                    
                    move_line = {
                         'name':line.name,
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
                    
                    if line.type == 'dr':
                        move_line.update({
                            'debit': line.amount or False
                        })
                        amount = line.amount
                    
                    elif line.type == 'cr':
                        move_line.update({
                            'credit': line.amount or False
                        })
                        amount = line.amount
                    
                    move_line_id = move_line_pool.create(cr, uid, move_line)
                    line_ids += [move_line_id]
                    
                    if line.move_id and inv.type in ('payment', 'receipt'):
                        rec_ids += [move_line_id]
                        for move_line in line.move_id.line_id:
                            if line.account_id.id == move_line.account_id.id:
                                rec_ids += [move_line.id]

            if rec_ids:
                move_line_pool.reconcile_partial(cr, uid, rec_ids)
            
            rec = {
                'move_id': move_id
            }
            
            message = _('Voucher ') + " '" + inv.name + "' "+ _("is confirm")
            self.log(cr, uid, inv.id, message)
            
            self.write(cr, uid, [inv.id], rec)
            move_pool.post(cr, uid, [move_id], context={})
            
        return True

account_voucher()

class account_voucher_line(osv.osv):
    _inherit = 'account.voucher.line'
    
    def default_get(self, cr, uid, fields, context={}):
        data = super(account_voucher_line, self).default_get(cr, uid, fields, context)
        self.voucher_context = context
        return data
    
    _columns = {
        'move_id' : fields.many2one('account.move','Bill / Invoice'),
    }

    def move_line_get_item(self, cr, uid, line, context={}):
        res = super(account_voucher_line, self).move_line_get_item(cr, uid, line, context)
        res['invoice'] = line.invoice_id or False
        return res
    
    def onchange_invoice_id(self, cr, uid, ids, invoice_id, currency_id):
        currency_pool = self.pool.get('res.currency')
        invoice_pool = self.pool.get('account.move')
        res = {
            
        }
        if not invoice_id:
            return {
                'value':res
            }
        else:
            invoice = invoice_pool.browse(cr, uid, invoice_id)
            residual = invoice.amount

            company_currency = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id
            currency_diff = company_currency != currency_id
            
            if currency_diff:
                residual = currency_pool.compute(cr, uid, company_currency, currency_id, residual)

            if residual > 0:
                res.update({
                    'amount': residual,
                    'ref':invoice.name
                })
            
        return {
            'value':res
        }

    def onchange_line_account(self, cr, uid, ids, account_id, type, type1):
        if not account_id:
            return {'value' : {'account_id' : False, 'type' : False ,'amount':False}}
        obj = self.pool.get('account.account')
        acc_id = False

        if type1 in ('receipt'):
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'cr'
        elif type1 in ('payment') :
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'dr'
        elif type1 in ('sale') :
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'dr'
        elif type1 in ('purchase') :
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'cr'

        return {
            'value' : {'type' : type, 'amount':balance}
        }
account_voucher_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

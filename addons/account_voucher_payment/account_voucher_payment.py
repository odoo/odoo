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


class account_move_line(osv.osv):
    _inherit = "account.move.line"
    _columns = {
        'voucher_invoice': fields.many2one('account.invoice', 'Invoice', readonly=True),
    }
account_move_line()

class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    _columns = {
        'voucher_line_ids':fields.one2many('account.voucher.line','voucher_id','Voucher Lines', readonly=False, states={'proforma':[('readonly',True)]}),
    }
        
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
            if inv.type in ('pay_voucher', 'journal_voucher', 'rec_voucher','cont_voucher','bank_pay_voucher','bank_rec_voucher','journal_sale_voucher','journal_pur_voucher'):
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                
            date = inv.date
            total_currency = 0
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
                'name': name, 
                'journal_id': journal_id, 
                'voucher_type':inv.type,
                'narration' : inv.narration,
                'data':date
            }
            
            if inv.period_id:
                move['period_id'] = inv.period_id.id
                for i in line:
                    i[2]['period_id'] = inv.period_id.id
            move_id = self.pool.get('account.move').create(cr, uid, move)
            ref=move['name']
            amount=0.0
            #create the first line our self
            move_line = {
                'name': inv.name,
                'voucher_invoice' : iml and iml[0]['invoice'] and iml[0]['invoice'].id or False,
                'debit': False,
                'credit':False,
                'account_id': inv.account_id.id or False,
                'move_id':move_id ,
                'journal_id':journal_id ,
                'period_id':inv.period_id.id,
                'partner_id': False,
                'ref': ref, 
                'date': date
            }
            if inv.type in ('rec_voucher', 'bank_rec_voucher', 'journal_pur_voucher', 'journal_voucher'):
                move_line['debit'] = inv.amount
            else:
                move_line['credit'] = inv.amount * (-1)
            self.pool.get('account.move.line').create(cr, uid, move_line)
            id_mapping_dict = {}
            mline_ids = []
            for line in inv.voucher_line_ids:
                move_line = {
                    'name':line.name,
                    'voucher_invoice' : iml and iml[0]['invoice'] and iml[0]['invoice'].id or False,
                    'debit':False,
                    'credit':False,
                    'move_id':move_id,                    
                    'account_id':line.account_id.id or False,
                    'journal_id':journal_id ,
                    'period_id':inv.period_id.id,
                    'partner_id':line.partner_id.id or False,
                    'ref':ref, 
                    'date':date
                 }
                
                if line.type == 'dr':
                    move_line['debit'] = line.amount or False
                    amount=line.amount
                elif line.type == 'cr':
                    move_line['credit'] = line.amount or False
                    amount=line.amount * (-1)
                ml_id=self.pool.get('account.move.line').create(cr, uid, move_line)
                id_mapping_dict[line.id] = ml_id
                
                total = 0.0
                mline = self.pool.get('account.move.line')
                if line.invoice_id.id:
                    invoice = self.pool.get('account.invoice').browse(cr, uid, line.invoice_id.id)
                    src_account_id = invoice.account_id.id
                    cr.execute('select id from account_move_line where move_id in ('+str(invoice.move_id.id)+')')
                    temp_ids = map(lambda x: x[0], cr.fetchall())
                    temp_ids.append(ml_id)
                    mlines = mline.browse(cr, uid, temp_ids)
                    for ml in mlines:
                        if ml.account_id.id==src_account_id:
                            mline_ids.append(ml.id)
                            total += (ml.debit or 0.0) - (ml.credit or 0.0)
                #end if line.invoice_id.id:
                if inv.narration:
                    line.name=inv.narration
                else:
                    line.name=line.name
                
                if line.account_analytic_id:
                    an_line = {
                         'name':line.name,
                         'date':date,
                         'amount':amount,
                         'account_id':line.account_analytic_id.id or False,
                         'move_id':ml_id,
                         'journal_id':an_journal_id ,
                         'general_account_id':line.account_id.id,
                         'ref':ref
                     }
                    self.pool.get('account.analytic.line').create(cr,uid,an_line)
            if mline_ids:
                self.pool.get('account.move.line').reconcile_partial(cr, uid, mline_ids, 'manual', context={})
            self.write(cr, uid, [inv.id], {'move_id': move_id})
            obj=self.pool.get('account.move').browse(cr, uid, move_id)
            
            for line in obj.line_id :
                cr.execute('insert into voucher_id (account_id,rel_account_move) values (%d, %d)',(int(ids[0]),int(line.id)))
                
        return True

account_voucher()

class account_voucher_line(osv.osv):
    _inherit = 'account.voucher.line'
    
    def default_get(self, cr, uid, fields, context={}):
        data = super(account_voucher_line, self).default_get(cr, uid, fields, context)
        self.voucher_context = context
        return data
    
    _columns = {
        'invoice_id' : fields.many2one('account.invoice','Invoice'),
    }

    def move_line_get_item(self, cr, uid, line, context={}):
        res = super(account_voucher_line, self).move_line_get_item(cr, uid, line, context)
        res['invoice'] = line.invoice_id or False
        return res 
    
    def onchange_invoice_id(self, cr, uid, ids, invoice_id, context={}):
        lines = []
        if 'lines' in self.voucher_context:
            lines = [x[2] for x in self.voucher_context['lines']]
        if not invoice_id:
            return {'value':{}}
        else:
            invoice_obj = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context)
            residual = invoice_obj.residual
            same_invoice_amounts = [x['amount'] for x in lines if x['invoice_id']==invoice_id]
            residual -= sum(same_invoice_amounts)
            return {'value' : {'amount':residual}}  
    
    def onchange_line_account(self, cr, uid, ids, account_id, type, type1):
        if not account_id:
            return {'value' : {'account_id' : False, 'type' : False ,'amount':False}}
        obj = self.pool.get('account.account')
        acc_id = False
        
        if type1 in ('rec_voucher','bank_rec_voucher', 'journal_voucher'):
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'cr'
        elif type1 in ('pay_voucher','bank_pay_voucher','cont_voucher') : 
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'dr'
        elif type1 in ('journal_sale_vou') : 
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.credit
            type = 'dr'
        elif type1 in ('journal_pur_voucher') : 
            acc_id = obj.browse(cr, uid, account_id)
            balance = acc_id.debit
            type = 'cr'

        return {
            'value' : {'type' : type, 'amount':balance}
        }
account_voucher_line()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    
    def action_cancel(self, cr, uid, ids, *args):
        res = super(account_invoice, self).action_cancel(cr, uid, ids, *args)
        invoices = self.read(cr, uid, ids, ['move_id'])
        voucher_db = self.pool.get('account.voucher')
        voucher_ids = voucher_db.search(cr, uid, [])
        voucher_obj = voucher_db.browse(cr, uid, voucher_ids)
        move_db = self.pool.get('account.move')
        move_ids = move_db.search(cr, uid, [])
        move_obj = move_db.browse(cr, uid, move_ids)
        return res
    
account_invoice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

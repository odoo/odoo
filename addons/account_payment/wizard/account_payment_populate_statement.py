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

from openerp.osv import fields, osv

class account_payment_populate_statement(osv.osv_memory):
    _name = "account.payment.populate.statement"
    _description = "Account Payment Populate Statement"
    _columns = {
        'lines': fields.many2many('payment.line', 'payment_line_rel_', 'payment_id', 'line_id', 'Payment Lines')
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        line_obj = self.pool.get('payment.line')

        res = super(account_payment_populate_statement, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        line_ids = line_obj.search(cr, uid, [
            ('move_line_id.reconcile_id', '=', False),
            ('bank_statement_line_id', '=', False),
            ('move_line_id.state','=','valid')])
        line_ids.extend(line_obj.search(cr, uid, [
            ('move_line_id.reconcile_id', '=', False),
            ('order_id.mode', '=', False),
            ('move_line_id.state','=','valid')]))
        domain = '[("id", "in", '+ str(line_ids)+')]'
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='lines']")
        for node in nodes:
            node.set('domain', domain)
        res['arch'] = etree.tostring(doc)
        return res

    def populate_statement(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('payment.line')
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        currency_obj = self.pool.get('res.currency')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        move_line_obj = self.pool.get('account.move.line')

        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        line_ids = data['lines']
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)

        for line in line_obj.browse(cr, uid, line_ids, context=context):
            ctx = context.copy()
            ctx['date'] = line.ml_maturity_date # was value_date earlier,but this field exists no more now
            amount = currency_obj.compute(cr, uid, line.currency.id,
                    statement.currency.id, line.amount_currency, context=ctx)

            if not line.move_line_id.id:
                continue
            context = dict(context, move_line_ids=[line.move_line_id.id])
            result = voucher_obj.onchange_partner_id(cr, uid, [], partner_id=line.partner_id.id, journal_id=statement.journal_id.id, amount=abs(amount), currency_id= statement.currency.id, ttype='payment', date=line.ml_maturity_date, context=context)

            if line.move_line_id:
                voucher_res = {
                        'type': 'payment',
                        'name': line.name,
                        'partner_id': line.partner_id.id,
                        'journal_id': statement.journal_id.id,
                        'account_id': result['value'].get('account_id', statement.journal_id.default_credit_account_id.id),
                        'company_id': statement.company_id.id,
                        'currency_id': statement.currency.id,
                        'date': line.date or time.strftime('%Y-%m-%d'),
                        'amount': abs(amount),
                        'period_id': statement.period_id.id,
                }
                voucher_id = voucher_obj.create(cr, uid, voucher_res, context=context)

                voucher_line_dict =  {}
                for line_dict in result['value']['line_cr_ids'] + result['value']['line_dr_ids']:
                    move_line = move_line_obj.browse(cr, uid, line_dict['move_line_id'], context)
                    if line.move_line_id.move_id.id == move_line.move_id.id:
                        voucher_line_dict = line_dict

                if voucher_line_dict:
                    voucher_line_dict.update({'voucher_id': voucher_id})
                    voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)
                st_line_id = statement_line_obj.create(cr, uid, {
                    'name': line.order_id.reference or '?',
                    'amount': - amount,
                    'partner_id': line.partner_id.id,
                    'statement_id': statement.id,
                    'ref': line.communication,
                    }, context=context)

                line_obj.write(cr, uid, [line.id], {'bank_statement_line_id': st_line_id})
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

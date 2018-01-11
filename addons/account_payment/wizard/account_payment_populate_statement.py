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

        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        line_ids = data['lines']
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)

        for line in line_obj.browse(cr, uid, line_ids, context=context):
            ctx = context.copy()
            ctx['date'] = line.ml_maturity_date  # was value_date earlier,but this field exists no more now
            amount = currency_obj.compute(cr, uid, line.currency.id,
                    statement.currency.id, line.amount_currency, context=ctx)

            st_line_vals = self._prepare_statement_line_vals(cr, uid, line, amount, statement, context=context)
            st_line_id = statement_line_obj.create(cr, uid, st_line_vals, context=context)

            line_obj.write(cr, uid, [line.id], {'bank_statement_line_id': st_line_id})
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_statement_line_vals(self, cr, uid, payment_line, amount,
                                     statement, context=None):
        return {
            'name': payment_line.order_id.reference or '?',
            'amount':-amount,
            'partner_id': payment_line.partner_id.id,
            'statement_id': statement.id,
            'ref': payment_line.communication,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

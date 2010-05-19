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
from lxml import etree

from osv import osv, fields

class account_payment_populate_statement(osv.osv_memory):
    _name = "account.payment.populate.statement"
    _description = "Account Payment Populate Statement"
    _columns = {
        'lines': fields.many2many('payment.line', 'payment_line_rel_', 'payment_id', 'line_id', 'Payment Lines')
               }

    def search_entries(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('payment.line')
        statement_obj = self.pool.get('account.bank.statement')
        mod_obj = self.pool.get('ir.model.data')

        data = self.read(cr, uid, ids, [], context=context)[0]
        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)
        line_ids = line_obj.search(cr, uid, [
            ('move_line_id.reconcile_id', '=', False),
            ('order_id.mode.journal.id', '=', statement.journal_id.id)])
        line_ids.extend(line_obj.search(cr, uid, [
            ('move_line_id.reconcile_id', '=', False),
            ('order_id.mode', '=', False)]))

        context.update({'line_ids': line_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','account_payment_populate_statement_view')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
                'name': ('Entrie Lines'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.payment.populate.statement',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(account_payment_populate_statement, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context and 'line_ids' in context:
            view_obj = etree.XML(res['arch'])
            child = view_obj.getchildren()[0]
            domain = '[("id", "in", '+ str(context['line_ids'])+')]'
            field = etree.Element('field', attrib={'domain': domain, 'name':'lines', 'colspan':'4', 'height':'300', 'width':'800', 'nolabel':"1"})
            child.addprevious(field)
            res['arch'] = etree.tostring(view_obj)
        return res

    def populate_statement(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('payment.line')
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        currency_obj = self.pool.get('res.currency')
        statement_reconcile_obj = self.pool.get('account.bank.statement.reconcile')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        line_ids = data['lines']
        if not line_ids:
            return {}

        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)

        for line in line_obj.browse(cr, uid, line_ids, context=context):
            ctx = context.copy()
            ctx['date'] = line.ml_maturity_date # was value_date earlier,but this field exists no more now
            amount = currency_obj.compute(cr, uid, line.currency.id,
                    statement.currency.id, line.amount_currency, context=ctx)

            if line.move_line_id:
                reconcile_id = statement_reconcile_obj.create(cr, uid, {
                    'line_ids': [(6, 0, [line.move_line_id.id])]
                    }, context=context)
                statement_line_obj.create(cr, uid, {
                    'name': line.order_id.reference or '?',
                    'amount': - amount,
                    'type': 'supplier',
                    'partner_id': line.partner_id.id,
                    'account_id': line.move_line_id.account_id.id,
                    'statement_id': statement.id,
                    'ref': line.communication,
                    'reconcile_id': reconcile_id,
                    }, context=context)
        return {'type' : 'ir.actions.act_window_close'}

account_payment_populate_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:>>>>>>> MERGE-SOURCE

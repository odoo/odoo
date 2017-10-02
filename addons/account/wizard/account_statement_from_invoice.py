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

from openerp import api
from openerp.osv import fields, osv

class account_statement_from_invoice_lines(osv.osv_memory):
    """
    Generate Entries by Statement from Invoices
    """
    _name = "account.statement.from.invoice.lines"
    _description = "Entries by Statement from Invoices"
    _columns = {
        'line_ids': fields.many2many('account.move.line', 'account_move_line_relation', 'move_id', 'line_id', 'Invoices'),
    }

    @api.model
    def _prepare_statement_line_vals(self, statement, line):
        amount = 0.0

        if line.debit > 0:
            amount = line.debit
        elif line.credit > 0:
            amount = -line.credit

        if line.amount_currency:
            if line.company_id.currency_id != statement.currency:
                # In the specific case where the company currency and the statement currency are the same
                # the debit/credit field already contains the amount in the right currency.
                # We therefore avoid to re-convert the amount in the currency, to prevent Gain/loss exchanges
                amount = line.currency_id.compute(
                    statement.currency, line.amount_currency)
        elif (line.invoice and line.invoice.currency_id != statement.currency):
            amount = line.invoice.currency_id.compute(
                statement.currency, amount)

        return {
            'name': line.name or '?',
            'amount': amount,
            'partner_id': line.partner_id.id,
            'statement_id': statement.id,
            'ref': line.ref,
            'date': statement.date,
            'amount_currency': line.amount_currency,
            'currency_id': line.currency_id.id,
        }

    def populate_statement(self, cr, uid, ids, context=None):
        context = dict(context or {})
        statement_id = context.get('statement_id', False)
        if not statement_id:
            return {'type': 'ir.actions.act_window_close'}
        data = self.read(cr, uid, ids, context=context)[0]
        line_ids = data['line_ids']
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        line_obj = self.pool.get('account.move.line')
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        statement = statement_obj.browse(cr, uid, statement_id, context=context)
        line_date = statement.date

        ctx = context.copy()
        #  take the date for computation of currency => use payment date
        ctx['date'] = line_date

        # for each selected move lines
        for line in line_obj.browse(cr, uid, line_ids, context=context):

            st_line_vals = self._prepare_statement_line_vals(
                cr, uid, ids, statement, line, context=ctx)

            context.update({'move_line_ids': [line.id],
                            'invoice_id': line.invoice.id})

            statement_line_obj.create(cr, uid, st_line_vals, context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

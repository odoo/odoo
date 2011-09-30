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
from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import osv, fields
from tools.translate import _
import pos_box_entries

class pos_box_out(osv.osv_memory):
    _name = 'pos.box.out'
    _description = 'Pos Box Out'

    def _get_expense_product(self, cr, uid, context=None):
        """
             Make the selection list of expense product.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        product_obj = self.pool.get('product.product')
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        ids = product_obj.search(cr, uid, ['&', ('expense_pdt', '=', True), '|', ('company_id', '=', company_id), ('company_id', '=', None)], context=context)
        res = product_obj.read(cr, uid, ids, ['id', 'name'], context=context)
        res = [(r['id'], r['name']) for r in res]
        res.insert(0, ('', ''))
        return res

    _columns = {
        'name': fields.char('Description', size=32, required=True),
        'journal_id': fields.selection(pos_box_entries.get_journal, "Cash Register", required=True),
        'product_id': fields.selection(_get_expense_product, "Operation", required=True),
        'amount': fields.float('Amount', digits=(16, 2)),
        'ref': fields.char('Ref', size=32),
    }
    _defaults = {
         'journal_id': 1,
         'product_id': 1,
    }
    def get_out(self, cr, uid, ids, context=None):

        """
         Create the entries in the CashBox   .
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return :Return of operation of product
        """
        vals = {}
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        product_obj = self.pool.get('product.template')
        productp_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.users')
        for data in  self.read(cr, uid, ids, context=context):
            curr_company = res_obj.browse(cr, uid, uid, context=context).company_id.id
            statement_id = statement_obj.search(cr, uid, [('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')], context=context)
            monday = (datetime.today() + relativedelta(weekday=0)).strftime('%Y-%m-%d')
            sunday = (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
            done_statmt = statement_obj.search(cr, uid, [('date', '>=', monday+' 00:00:00'), ('date', '<=', sunday+' 23:59:59'), ('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid)], context=context)
            stat_done = statement_obj.browse(cr, uid, done_statmt, context=context)
            address_u = res_obj.browse(cr, uid, uid, context=context).address_id
            am = 0.0

            amount_check = productp_obj.browse(cr, uid, data['product_id'], context=context).am_out or False
            for st in stat_done:
                for s in st.line_ids:
                    if address_u and s.partner_id == address_u.partner_id and s.am_out:
                        am += s.amount
            if (-data['amount'] or 0.0) + am < -(res_obj.browse(cr, uid, uid, context=context).company_id.max_diff or 0.0) and amount_check:
                val = (res_obj.browse(cr, uid, uid).company_id.max_diff or 0.0) + am
                raise osv.except_osv(_('Error !'), _('The maximum value you can still withdraw is exceeded. \n Remaining value is equal to %s ')%(val))

            acc_id = product_obj.browse(cr, uid, data['product_id'], context=context).property_account_income
            if not acc_id:
                raise osv.except_osv(_('Error !'), _('please check that account is set to %s')%(product_obj.browse(cr, uid, data['product_id'], context=context).name))
            if not statement_id:
                raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
            if statement_id:
                statement_id = statement_id[0]
            if not statement_id:
                statement_id = statement_obj.create(cr, uid, {
                                    'date': time.strftime('%Y-%m-%d 00:00:00'),
                                    'journal_id': data['journal_id'],
                                    'company_id': curr_company,
                                    'user_id': uid,
                                }, context=context)
            vals['statement_id'] = statement_id
            vals['journal_id'] = data['journal_id']
            if acc_id:
                vals['account_id'] = acc_id.id
            amount = data['amount'] or 0.0
            if data['amount'] > 0:
                amount = -data['amount']
            vals['amount'] = amount
            if productp_obj.browse(cr, uid, data['product_id'], context=context).am_out:
                vals['am_out'] = True
            vals['ref'] = data['ref'] or ''
            vals['name'] = "%s: %s " % (product_obj.browse(cr, uid, data['product_id'], context=context).name, data['name'].decode('utf8'))
            address_u = res_obj.browse(cr, uid, uid, context=context).address_id
            if address_u:
                vals['partner_id'] = address_u.partner_id and address_u.partner_id.id or None
            statement_line_obj.create(cr, uid, vals, context=context)
        return {}

pos_box_out()


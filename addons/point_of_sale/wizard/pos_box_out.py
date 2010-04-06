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

from osv import osv, fields
import time
from tools.translate import _
from mx import DateTime
import pos_box_entries


class pos_box_out(osv.osv_memory):
    _name = 'pos.box.out'
    _description = 'Pos Box Out'

    def _get_expense_product(self, cr, uid, context):

        """
             Make the selection list of expense product.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        obj = self.pool.get('product.product')
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        ids = obj.search(cr, uid, ['&', ('expense_pdt', '=', True), '|', ('company_id', '=', company_id), ('company_id', '=', None)])
        res = obj.read(cr, uid, ids, ['id', 'name'], context)
        res = [(r['id'], r['name']) for r in res]
        res.insert(0, ('', ''))
        return res

    _columns = {
                'name': fields.char('Name', size=32, required=True),
                'journal_id': fields.selection(pos_box_entries.get_journal, "Journal", required=True),
                'product_id': fields.selection(_get_expense_product, "Operation", required=True),
                'amount': fields.float('Amount', digits=(16, 2)),
                'ref': fields.char('Ref', size=32),
    }
    _defaults = {
                 'journal_id': lambda *a: 1,
                 'product_id': lambda *a: 1,
                }
    def get_out(self, cr, uid, ids, context):

        """
             Create the entries in the CashBox   .
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        args = {}
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        product_obj = self.pool.get('product.template')
        productp_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.users')
        for data in  self.read(cr, uid, ids):
            curr_company = res_obj.browse(cr, uid, uid).company_id.id
            statement_id = statement_obj.search(cr, uid, [('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')])
            monday = (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Monday, 0))).strftime('%Y-%m-%d')
            sunday = (DateTime.now() + DateTime.RelativeDateTime(weekday=(DateTime.Sunday, 0))).strftime('%Y-%m-%d')
            done_statmt = statement_obj.search(cr, uid, [('date', '>=', monday+' 00:00:00'), ('date', '<=', sunday+' 23:59:59'), ('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid)])
            stat_done = statement_obj.browse(cr, uid, done_statmt)
            address_u = res_obj.browse(cr, uid, uid).address_id
            am = 0.0

            amount_check = productp_obj.browse(cr, uid, data['product_id']).am_out or False
            for st in stat_done:
                for s in st.line_ids:
                    if address_u and s.partner_id == address_u.partner_id and s.am_out:
                        am += s.amount
            if (-data['amount'] or 0.0) + am < -(res_obj.browse(cr, uid, uid).company_id.max_diff or 0.0) and amount_check:
                val = (res_obj.browse(cr, uid, uid).company_id.max_diff or 0.0) + am
                raise osv.except_osv(_('Error !'), _('The maximum value you can still withdraw is exceeded. \n Remaining value is equal to %d ')%(val))

            acc_id = product_obj.browse(cr, uid, data['product_id']).property_account_income
            if not acc_id:
                raise osv.except_osv(_('Error !'), _('please check that account is set to %s')%(product_obj.browse(cr, uid, data['product_id']).name))
            if not statement_id:
                raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
            if statement_id:
                statement_id = statement_id[0]
            if not statement_id:
                statement_id = statement_obj.create(cr, uid, {'date': time.strftime('%Y-%m-%d 00:00:00'),
                                                'journal_id': data['journal_id'],
                                                'company_id': curr_company,
                                                'user_id': uid,
                                                })
            args['statement_id'] = statement_id
            args['journal_id'] = data['journal_id']
            if acc_id:
                args['account_id'] = acc_id.id
            amount = data['amount'] or 0.0
            if data['amount'] > 0:
                amount = -data['amount']
            args['amount'] = amount
            if productp_obj.browse(cr, uid, data['product_id']).am_out:
                args['am_out'] = True
            args['ref'] = data['ref'] or ''
            args['name'] = "%s: %s " % (product_obj.browse(cr, uid, data['product_id']).name, data['name'].decode('utf8'))
            address_u = res_obj.browse(cr, uid, uid).address_id
            if address_u:
                partner_id = address_u.partner_id and address_u.partner_id.id or None
                args['partner_id'] = partner_id
            statement_line_id = statement_line_obj.create(cr, uid, args)
        return {}

pos_box_out()


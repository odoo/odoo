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
        return res

    _columns = {
        'name': fields.char('Description / Reason', size=32, required=True),
        'journal_id': fields.selection(pos_box_entries.get_journal, "Cash Register", required=True, size=-1),
        'product_id': fields.selection(_get_expense_product, "Operation", required=True, size=-1),
        'amount': fields.float('Amount', digits=(16, 2), required=True),
        'session_id' : fields.many2one('pos.session', 'Session'),
        'user_id' : fields.many2one('res.users', 'User'),
    }
    _defaults = {
        'journal_id': 1,
        'product_id': 1,
        'user_id' : lambda obj, cr, uid, context: uid,
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
        product_obj = self.pool.get('product.product')
        res_obj = self.pool.get('res.users')
        for data in  self.read(cr, uid, ids, context=context):
            curr_company = res_obj.browse(cr, uid, uid, context=context).company_id.id
            statement_ids = statement_obj.search(cr, uid, [('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')], context=context)
            monday = (datetime.today() + relativedelta(weekday=0)).strftime('%Y-%m-%d')
            sunday = (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
            done_statmt = statement_obj.search(cr, uid, [('date', '>=', monday+' 00:00:00'), ('date', '<=', sunday+' 23:59:59'), ('journal_id', '=', data['journal_id']), ('company_id', '=', curr_company), ('user_id', '=', uid)], context=context)
            stat_done = statement_obj.browse(cr, uid, done_statmt, context=context)
            am = 0.0
            product = product_obj.browse(cr, uid, data['product_id'], context=context)
            acc_id = product.property_account_expense or product.categ_id.property_account_expense_categ
            if not acc_id:
                raise osv.except_osv(_('Error!'), _('please check that account is set to %s.')%(product.name))
            if not statement_ids:
                raise osv.except_osv(_('Error!'), _('You have to open at least one cashbox.'))
            vals['statement_id'] = statement_ids[0]
            vals['journal_id'] = data['journal_id']
            vals['account_id'] = acc_id.id
            amount = data['amount'] or 0.0
            if data['amount'] > 0:
                amount = -data['amount']
            vals['amount'] = amount
            vals['name'] = "%s: %s " % (product.name, data['name'])
            statement_line_obj.create(cr, uid, vals, context=context)
        return {}

pos_box_out()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

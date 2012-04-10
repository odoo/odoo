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

from osv import osv, fields
from tools.translate import _


def get_journal(self, cr, uid, context=None):
    """
         Make the selection list of Cash Journal  .
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return :Return the list of journal
    """

    journal_obj = self.pool.get('account.journal')
    statement_obj = self.pool.get('account.bank.statement')

    j_ids = journal_obj.search(cr, uid, [('journal_user','=',1)], context=context)
    obj_ids = statement_obj.search(cr, uid, [('state', '=', 'open'), ('user_id', '=', uid), ('journal_id', 'in', j_ids)], context=context)
    res = statement_obj.read(cr, uid, obj_ids, ['journal_id'], context=context)
    res = [(r['journal_id']) for r in res]
    if not len(res):
        raise osv.except_osv(_('Error !'), _('You do not have any open cash register. You must create a payment method or open a cash register.'))
    return res

class pos_box_entries(osv.osv_memory):
    _name = 'pos.box.entries'
    _description = 'Pos Box Entries'

    def _get_income_product(self, cr, uid, context=None):
        """
             Make the selection list of purchasing  products.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        product_obj = self.pool.get('product.product')
        ids = product_obj.search(cr, uid, [('income_pdt', '=', True)], context=context)
        res = product_obj.read(cr, uid, ids, ['id', 'name'], context=context)
        res = [(r['id'], r['name']) for r in res]
        res.insert(0, ('', ''))

        return res

    _columns = {
        'name': fields.char('Reason', size=32, required=True),
        'journal_id': fields.selection(get_journal, "Cash Register", required=True, size=-1),
        'product_id': fields.selection(_get_income_product, "Operation", required=True, size=-1),
        'amount': fields.float('Amount', digits=(16, 2), required=True),
        'ref': fields.char('Ref', size=32),
        'session_id' : fields.many2one('pos.session', 'Session'),
        'user_id' : fields.many2one('res.users', 'User'),
    }
    _defaults = {
        'journal_id': 1,
        'product_id': 1,
        'user_id' : lambda obj, cr, uid, context: uid,
    }

    def get_in(self, cr, uid, ids, context=None):
        """
             Create the entry of statement in journal.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return :Return of operation of product
        """
        statement_obj = self.pool.get('account.bank.statement')
        res_obj = self.pool.get('res.users')
        product_obj = self.pool.get('product.product')
        bank_statement = self.pool.get('account.bank.statement.line')
        for data in  self.read(cr, uid, ids, context=context):
            vals = {}
            curr_company = res_obj.browse(cr, uid, uid, context=context).company_id.id
            statement_id = statement_obj.search(cr, uid, [('journal_id', '=', int(data['journal_id'])), ('company_id', '=', curr_company), ('user_id', '=', uid), ('state', '=', 'open')], context=context)
            if not statement_id:
                raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))

            product = product_obj.browse(cr, uid, int(data['product_id']))
            acc_id = product.property_account_income or product.categ_id.property_account_income_categ
            if not acc_id:
                raise osv.except_osv(_('Error !'), _('Please check that income account is set to %s')%(product_obj.browse(cr, uid, data['product_id']).name))
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
            vals['amount'] = data['amount'] or 0.0
            vals['ref'] = "%s" % (data['ref'] or '')
            vals['name'] = "%s: %s " % (product_obj.browse(cr, uid, data['product_id'], context=context).name, data['name'].decode('utf8'))
            bank_statement.create(cr, uid, vals, context=context)
        return {}

pos_box_entries()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

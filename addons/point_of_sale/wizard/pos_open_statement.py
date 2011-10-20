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

from osv import osv
from tools.translate import _

class pos_open_statement(osv.osv_memory):
    _name = 'pos.open.statement'
    _description = 'Open Statements'

    def open_statement(self, cr, uid, ids, context=None):
        """
             Open the statements
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Blank Directory
        """
        data = {}
        mod_obj = self.pool.get('ir.model.data')
        statement_obj = self.pool.get('account.bank.statement')
        sequence_obj = self.pool.get('ir.sequence')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}

        st_ids = []
        j_ids = journal_obj.search(cr, uid, [('journal_user','=',1)], context=context)

        for journal in journal_obj.browse(cr, uid, j_ids, context=context):
            ids = statement_obj.search(cr, uid, [('state', '!=', 'confirm'), ('user_id', '=', uid), ('journal_id', '=', journal.id)], context=context)
            if len(ids):
                st_ids += ids
                continue

            if journal.sequence_id:
                number = sequence_obj.next_by_id(cr, uid, journal.sequence_id.id)
            else:
                number = sequence_obj.next_by_code(cr, uid, 'account.cash.statement')

            data.update({
                'journal_id': journal.id,
                'user_id': uid,
                'state': 'draft',
                'name': number 
            })
            statement_id = statement_obj.create(cr, uid, data, context=context)
            st_ids.append(statement_id)

            if journal.auto_cash:
                statement_obj.button_open(cr, uid, [statement_id], context)

        tree_res = mod_obj.get_object_reference(cr, uid, 'point_of_sale', 'view_cash_statement_pos_tree')
        tree_id = tree_res and tree_res[1] or False
        form_res = mod_obj.get_object_reference(cr, uid, 'account', 'view_bank_statement_form2')
        form_id = form_res and form_res[1] or False
        search_id = mod_obj.get_object_reference(cr, uid, 'point_of_sale', 'view_pos_open_cash_statement_filter')

        return {
            'domain': "[('id', 'in',[ "+','.join(map(str,st_ids))+"])]",
            'name': _('Open Cash Registers'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'search_view_id': search_id and search_id[1] or False ,
            'res_model': 'account.bank.statement',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'context': {},
            'type': 'ir.actions.act_window'
        }
pos_open_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

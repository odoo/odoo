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
import time

class pos_open_statement(osv.osv_memory):
    _name = 'pos.open.statement'
    _description = 'Open Statements'

    def open_statement(self, cr, uid, ids, context):
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
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        statement_obj = self.pool.get('account.bank.statement')
        sequence_obj = self.pool.get('ir.sequence')
        journal_obj = self.pool.get('account.journal')
        cr.execute("""select DISTINCT journal_id from pos_journal_users where user_id=%d order by journal_id"""%(uid))
        j_ids = map(lambda x1: x1[0], cr.fetchall())
        journal_ids = journal_obj.search(cr, uid, [('auto_cash', '=', True), ('type', '=', 'cash'), ('id', 'in', j_ids)])

        for journal in journal_obj.browse(cr, uid, journal_ids):
            ids = statement_obj.search(cr, uid, [('state', '!=', 'confirm'), ('user_id', '=', uid), ('journal_id', '=', journal.id)])
            if len(ids):
                raise osv.except_osv(_('Message'), _('You can not open a Cashbox for "%s".\nPlease close its related Register.' %(journal.name)))

            statement_ids = sorted(statement_obj.search(cr, uid, [('state', '=', 'confirm'), ('user_id', '=', uid), ('journal_id', '=', journal.id)]))
            if statement_ids:
                res = []
                statement_ids.reverse()
                statement = statement_obj.browse(cr, uid, statement_ids[0])
                for end_bal in statement.ending_details_ids:
                    dct = {
                            'pieces': end_bal.pieces,
                            'number': end_bal.number,
                    }
                    res.append((0, 0, dct))
                data['starting_details_ids'] = res
            else:
                data['starting_details_ids'] = statement_obj._get_cash_close_box_lines(cr, uid, [])

            number = ''
            if journal.sequence_id:
                number = sequence_obj.get_id(cr, uid, journal.sequence_id.id)
            else:
                number = sequence_obj.get(cr, uid, 'account.bank.statement')

            data.update({'journal_id': journal.id,
                         'company_id': company_id,
                         'user_id': uid,
                         'state': 'open',
                         'name': number })
            statement_id = statement_obj.create(cr, uid, data)
            statement_obj.button_open(cr, uid, [statement_id], context)

        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'account', 'view_bank_statement_tree')
        id3 = data_obj._get_id(cr, uid, 'account', 'view_bank_statement_form2')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        return {
            'domain': "[('state','=','open')]",
            'name': 'Open Statement',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.bank.statement',
            'views': [(id2, 'tree'),(id3, 'form')],
            'type': 'ir.actions.act_window'
        }
pos_open_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

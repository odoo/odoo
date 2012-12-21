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

from openerp.osv import osv

class account_journal_select(osv.osv_memory):
    """
        Account Journal Select
    """
    _name = "account.journal.select"
    _description = "Account Journal Select"

    def action_open_window(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if context is None:
            context = {}

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_move_line_select')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id])[0]
        cr.execute('select journal_id, period_id from account_journal_period where id=%s', (context['active_id'],))
        res = cr.fetchone()
        if res:
            journal_id, period_id = res
            result['domain'] = str([('journal_id', '=', journal_id), ('period_id', '=', period_id)])
            result['context'] = str({'journal_id': journal_id, 'period_id': period_id})
        return result

account_journal_select()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

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

class account_move_line_select(osv.osv_memory):
    """
        Account move line select
    """
    _name = "account.move.line.select"
    _description = "Account move line select"

    def open_window(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        account_obj = self.pool.get('account.account')
        fiscalyear_obj = self.pool.get('account.fiscalyear')

        if context is None:
            context = {}

        if 'fiscalyear' not in context:
            fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyears = fiscalyear_obj.browse(cr, uid, fiscalyear_ids, context=context)

        period_ids = []
        if fiscalyears:
            for fiscalyear in fiscalyears:
                for period in fiscalyear.period_ids:
                    period_ids.append(period.id)
            domain = str(('period_id', 'in', period_ids))

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_move_line_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id])[0]
        result['context'] = {
            'fiscalyear': False,
            'account_id': context['active_id'],
            'active_id': context['active_id'],
        }

        if context['active_id']:
            acc_data = account_obj.browse(cr, uid, context['active_id']).child_consol_ids
            if acc_data:
                result['context'].update({'consolidate_children': True})
        result['domain']=result['domain'][0:-1]+','+domain+result['domain'][-1]
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

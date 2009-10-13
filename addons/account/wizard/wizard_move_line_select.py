# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import pooler

class wizard_move_line_select(wizard.interface):
    def _open_window(self, cr, uid, data, context):
        mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
        act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')
        account_obj = pooler.get_pool(cr.dbname).get('account.account')
        fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')

        if not context.get('fiscalyear', False):
            fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyears = fiscalyear_obj.browse(cr, uid, fiscalyear_ids)
        period_ids = []
        for fiscalyear in fiscalyears:
            for period in fiscalyear.period_ids:
                period_ids.append(period.id)
        domain = str(('period_id', 'in', period_ids))

        result = mod_obj._get_id(cr, uid, 'account', 'action_move_line_tree1')
        id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
        result = act_obj.read(cr, uid, [id])[0]
        result['context'] = {
            'fiscalyear': context.get('fiscalyear', False),
            'account_id': data['id']
        }
        if data['id']:
            acc_data = account_obj.browse(cr, uid, data['id']).child_consol_ids
            if acc_data:
                result['context'].update({'consolidate_childs': True})
        result['domain']=result['domain'][0:-1]+','+domain+result['domain'][-1]
        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': _open_window, 'state': 'end'}
        }
    }
wizard_move_line_select('account.move.line.select')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


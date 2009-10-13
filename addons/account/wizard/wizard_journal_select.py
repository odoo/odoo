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

def _action_open_window(self, cr, uid, data, context):
    mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
    act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')

    result = mod_obj._get_id(cr, uid, 'account', 'action_move_line_select')
    id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
    result = act_obj.read(cr, uid, [id])[0]

    cr.execute('select journal_id,period_id from account_journal_period where id=%s', (data['id'],))
    journal_id,period_id = cr.fetchone()

    result['domain'] = str([('journal_id', '=', journal_id), ('period_id', '=', period_id)])
    result['context'] = str({'journal_id': journal_id, 'period_id': period_id})
    return result

class wiz_journal(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
wiz_journal('account.move.journal.select')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


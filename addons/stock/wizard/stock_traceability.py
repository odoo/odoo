# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import netsvc
import time
import pooler

from osv import osv

def action_traceability(type='move_history_ids', field='tracking_id'):
    def open_tab(self, cr, uid, data, context):
        obj = pooler.get_pool(cr.dbname).get('stock.move')
        ids = obj.search(cr, uid, [(field, 'in', data['ids'])])
        cr.execute('select id from ir_ui_view where model=%s and field_parent=%s and type=%s', ('stock.move', type, 'tree'))
        view_id = cr.fetchone()[0]
        value = {
            'domain': "[('id','in',["+','.join(map(str,ids))+"])]",
            'name': ((type=='move_history_ids') and 'Upstream Traceability') or 'Downstream Traceability',
            'view_type': 'tree',
            'res_model': 'stock.move',
            'field_parent': type,
            'view_id': (view_id,'View'),
            'type': 'ir.actions.act_window'
        }
        return value
    return open_tab

class wiz_journal(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability('move_history_ids2'), 'state':'end'}
        }
    }
wiz_journal('stock.traceability.downstream')

class wiz_journal2(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability(), 'state':'end'}
        }
    }
wiz_journal2('stock.traceability.upstream')

class wiz_journal3(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability(field='prodlot_id'), 'state':'end'}
        }
    }
wiz_journal3('stock.traceability.lot.upstream')

class wiz_journal4(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability('move_history_ids2', 'prodlot_id'), 'state':'end'}
        }
    }
wiz_journal4('stock.traceability.lot.downstream')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


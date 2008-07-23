# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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
            'result': {'type': 'action', 'action': action_traceability(), 'state':'end'}
        }
    }
wiz_journal('stock.traceability.aval')

class wiz_journal2(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability('move_history_ids2'), 'state':'end'}
        }
    }
wiz_journal2('stock.traceability.amont')

class wiz_journal3(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability(field='prodlot_id'), 'state':'end'}
        }
    }
wiz_journal3('stock.traceability.lot.amont')

class wiz_journal4(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': action_traceability('move_history_ids2', 'prodlot_id'), 'state':'end'}
        }
    }
wiz_journal4('stock.traceability.lot.aval')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import pooler

import time
from osv import osv
from tools.misc import UpdateableStr

#FIXME: this is not concurrency-safe !!!
arch = UpdateableStr()
fields = {}

def _get_moves(self, cr, uid, data, context):
	pick_obj = pooler.get_pool(cr.dbname).get('stock.picking')
	pick = pick_obj.browse(cr, uid, [data['id']])[0]
	res = {}
	fields.clear()
	arch_lst = ['<?xml version="1.0"?>', '<form string="Track lines">', '<label colspan="4" string="The first field of each line set the number of line this lot will be splitted into. A quantity of zero will not change the line. The second says if this lot should be tracked or not." />']
	for m in [line for line in pick.move_lines]:
		quantity = m.product_qty
		arch_lst.append('<field name="move%s"/><field name="track%s" />\n<newline />' % (m.id, m.id))
		fields['move%s' % m.id] = {'string' : m.product_id.name, 'type' : 'integer', 'default' : lambda x,y,z: 1}
		fields['track%s' % m.id] = {'string' : 'Tracking ?', 'type' : 'boolean', 'default' : lambda x,y,z: False}
		res.setdefault('moves', []).append(m.id)
	arch_lst.append('</form>')
	arch.string = '\n'.join(arch_lst)
	return res

def _split_lines(self, cr, uid, data, context):
	track_obj = pooler.get_pool(cr.dbname).get('stock.tracking')
	move_obj = pooler.get_pool(cr.dbname).get('stock.move')
	for move in move_obj.browse(cr, uid, data['form']['moves']):
		if data['form']['move%s' % move.id]:
			num_pack = move.product_qty / data['form']['move%s' % move.id] 
		for idx in range(data['form']['move%s' % move.id]):
			update_val = {'product_qty' : num_pack}
			if idx:
				current_move = move_obj.copy(cr, uid, move.id, {'state' : move.state})
			else:
				current_move = move.id
			if data['form']['track%s' % move.id]:
				new_tracking = track_obj.create(cr, uid, {'move_ids' : [(6, 0, [current_move])]})
				update_val['tracking_id'] = new_tracking 
			move_obj.write(cr, uid, [current_move], update_val)
	return {}

class wizard_track_move(wizard.interface):
	states = {
		'init': {
			'actions': [_get_moves],
			'result': {'type':'form', 'arch':arch, 'fields':fields, 'state':[('end','Cancel'),('split','Track')]}
		},
		'split': {
			'actions': [_split_lines],
			'result': {'type':'state', 'state':'end'}
		}
	}

wizard_track_move('stock.move.track')


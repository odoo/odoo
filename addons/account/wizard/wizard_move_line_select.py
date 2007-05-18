##############################################################################
#
# Copyright (c) 2005-2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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
import pooler

class wizard_move_line_select(wizard.interface):
	def _open_window(self, cr, uid, data, context):
		mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
		act_obj = pooler.get_pool(cr.dbname).get('ir.actions.act_window')
		fiscalyear_obj = pooler.get_pool(cr.dbname).get('account.fiscalyear')

		if not 'fiscalyear' in context:
			context['fiscalyear'] = fiscalyear_obj.find(cr, uid)

		fy = fiscalyear_obj.browse(cr, uid, [context['fiscalyear']])[0]
		domain = str(('period_id', 'in', [x.id for x in fy.period_ids]))

		result = mod_obj._get_id(cr, uid, 'account', 'action_move_line_tree1')
		id = mod_obj.read(cr, uid, [result], ['res_id'])[0]['res_id']
		result = act_obj.read(cr, uid, [id])[0]
		result['context'] = str({'fiscalyear': context['fiscalyear']})
		result['domain']=result['domain'][0:-1]+','+domain+result['domain'][-1]
		return result

	states = {
		'init': {
			'actions': [],
			'result': {'type': 'action', 'action': _open_window, 'state': 'end'}
		}
	}
wizard_move_line_select('account.move.line.select')


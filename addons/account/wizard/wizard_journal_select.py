##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

def _action_open_window(self, cr, uid, data, context):
	cr.execute('select id,name from ir_ui_view where model=%s and type=%s', ('account.move.line', 'form'))
	view_res = cr.fetchone()
	cr.execute('select journal_id,period_id from account_journal_period where id=%d', (data['id'],))
	journal_id,period_id = cr.fetchone()
	return {
		'domain': "[('journal_id','=',%d), ('period_id','=',%d)]" % (journal_id,period_id),
		#'name': 'Saisie Standard',
		'view_type': 'form',
		'view_mode': 'tree,form',
		'res_model': 'account.move.line',
		'view_id': view_res,
		'context': "{'journal_id':%d, 'period_id':%d}" % (journal_id,period_id),
		'type': 'ir.actions.act_window'
	}

class wiz_journal(wizard.interface):
	states = {
		'init': {
			'actions': [],
			'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
		}
	}
wiz_journal('account.move.journal.select')


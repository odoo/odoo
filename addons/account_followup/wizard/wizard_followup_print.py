##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import datetime
import pooler

_followup_wizard_all_form = """<?xml version="1.0"?>
<form string="Select partners" colspan="4">
	<field name="partner_ids"/>
</form>"""

_followup_wizard_all_fields = {
	'partner_ids': {
		'string': "Partners", 
		'type': 'many2many', 
		'relation': 'account_followup.stat',
	},
}


class followup_all_print(wizard.interface):
	def _get_partners(self, cr, uid, data, context):
		cr.execute('select id from account_followup_stat')
		ids = map(lambda x: x[0], cr.fetchall())
		return {'partner_ids': ids}

	def _update_partners(self, cr, uid, data, context):
		partner_ids = data['form']['partner_ids'][0][2]
		cr.execute(
			"SELECT l.partner_id, l.followup_line_id, l.date, l.id "\
			"FROM account_move_line AS l LEFT JOIN account_account AS a "\
				"ON (l.account_id=a.id) "\
			"WHERE (l.reconcile_id IS NULL) "\
				"AND (a.type='receivable') AND (l.debit > 0) "\
				"AND (l.state<>'draft') "\
				"AND partner_id in ("+','.join(map(str,partner_ids))+") "\
			"ORDER BY l.date")
		move_lines = cr.fetchall()

		old = None
		fups = {}
		fup_ids = pooler.get_pool(cr.dbname).get('account_followup.followup').search(cr, uid, [])
		if not fup_ids:
			raise wizard.except_wizard('No Follow up Defined', 
				'You must define at least one follow up for your company !')
		fup_id = fup_ids[0]

		# fups = {
		#     previous fup line id: (limit date for current fup line, 
		#                            current fup line id),
		#     ...
		# }
		current_date = datetime.date.today()
		cr.execute(
			"SELECT * "\
			"FROM account_followup_followup_line "\
			"WHERE followup_id=%d "\
			"ORDER BY sequence", (fup_id,))
		for result in cr.dictfetchall():
			# compute date from when move lines entered earlier than it need 
			# a follow up
			delay = datetime.timedelta(days=result['delay'])
			fups[old] = (current_date - delay, result['id'])
			if result['start'] == 'end_of_month':
				#CHECKME: I have a bad feeling about this...
				# but it depends on the semantic of the field, which I don't
				# know
				fups[old][0].replace(day=1)
			# old = id of previous fup line
			old = result['id']

		# we don't want any followup after the last one
		fups[old] = (datetime.date(datetime.MAXYEAR, 12, 31), old)

		partner_list = []
		for partner_id, followup_line_id, date, id in move_lines: 
			if (partner_id in partner_list) or (not partner_id):
				continue
				
			# if the move line has already a followup line but it is invalid,
			# we just skip the move line. 
			# Note that having no follow-up line *is* valid because of the way 
			# fups is constructed (fups[None] = ...)
			if followup_line_id not in fups:
				continue
				
			# if the move_line happened before the limit date for this level 
			# of followup, we mark the partner as needing a follow up, and
			# mark the line has having had this level of follow up
			if date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
				partner_list.append(partner_id)
				cr.execute(
					"UPDATE account_move_line "\
					"SET followup_line_id=%d, followup_date=%s "\
					"WHERE id=%d", 
					(fups[followup_line_id][1], 
					current_date.strftime('%Y-%m-%d'), id,))
		return {'partner_id': partner_list}

	states = {
		'init' : {
			'actions': [_get_partners],
			'result': {'type': 'form',
				'arch':_followup_wizard_all_form,
				'fields':_followup_wizard_all_fields,
				'state':[('end','Cancel'),('print','Print Follow Ups')]
			},
		},
		'print': {
			'actions': [_update_partners],
			'result': {'type':'print', 'report':'account_followup.followup.print', 'state':'end'},
		},

	}
followup_all_print('account_followup.followup.print.all')


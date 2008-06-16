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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

from osv import fields, osv
from mx import DateTime

class Invoice(osv.osv):
	_inherit = 'account.invoice'

	def _amount_to_pay(self, cursor, user, ids, name, args, context=None):
		'''Return the amount still to pay regarding all the payment orders'''
		if not ids:
			return {}
		res = {}
		for invoice in self.browse(cursor, user, ids, context=context):
			res[invoice.id] = 0.0
			if invoice.move_id:
				for line in invoice.move_id.line_id:
					if not line.date_maturity or \
							DateTime.strptime(line.date_maturity, '%Y-%m-%d') \
							< DateTime.now():
						res[invoice.id] += line.amount_to_pay
		return res

	_columns = {
		'amount_to_pay': fields.function(_amount_to_pay, method=True,
			type='float', string='Amount to be paid',
			help='The amount which should be paid at the current date\n' \
					'minus the amount which is already in payment order'),
	}

Invoice()

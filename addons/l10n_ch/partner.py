# -*- encoding: utf-8 -*-
#
#  bank.py
#  partner.py
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
##############################################################################
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

import netsvc
from osv import fields, osv

class res_partner(osv.osv):
	_inherit = 'res.partner'

	_columns = {
		'ref_companies': fields.one2many('res.company', 'partner_id',
		'Companies that refers to partner'),
	}



res_partner()



class res_partner_bank(osv.osv):
	_inherit = "res.partner.bank"
	_columns = {
		'name': fields.char('Description', size=128, required=True),
		'post_number': fields.char('Post number', size=64),
		'bvr_number': fields.char('BVR account number', size=11),
		'bvr_adherent_num': fields.char('BVR adherent number', size=11),
		'dta_code': fields.char('DTA code', size=5),
	}

	def _default_value(self, cursor, user, field, context=None):
		if field in ('country_id', 'state_id'):
			value = False
		else:
			value = ''
		if not context.get('address', False):
			return value
		for ham, spam, address in context['address']:
			if 'type' in address.keys() :
				if address['type'] == 'default':
					if field in address.keys():
						return address[field]
					else:
						return False
				elif not address['type']:
					value = address[field]
			else :
				value = False
		return value


	def name_get(self, cr, uid, ids, context=None):
		if not len(ids):
			return []
		bank_type_obj = self.pool.get('res.partner.bank.type')

		type_ids = bank_type_obj.search(cr, uid, [])
		bank_type_names = {}
		for bank_type in bank_type_obj.browse(cr, uid, type_ids,
				context=context):
			bank_type_names[bank_type.code] = bank_type.name
		res = []
		for r in self.read(cr, uid, ids, ['name','state'], context):
			res.append((r['id'], r['name']+' : '+bank_type_names[r['state']]))
		return res

	_sql_constraints = [
		('bvr_adherent_uniq', 'unique (bvr_adherent_num)', 'The BVR adherent number must be unique !')
	]


res_partner_bank()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

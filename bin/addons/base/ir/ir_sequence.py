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

import time
from osv import fields,osv

class ir_sequence_type(osv.osv):
	_name = 'ir.sequence.type'
	_columns = {
		'name': fields.char('Sequence Name',size=64, required=True),
		'code': fields.char('Sequence Code',size=32, required=True),
	}
ir_sequence_type()

def _code_get(self, cr, uid, context={}):
	cr.execute('select code, name from ir_sequence_type')
	return cr.fetchall()

class ir_sequence(osv.osv):
	_name = 'ir.sequence'
	_columns = {
		'name': fields.char('Sequence Name',size=64, required=True),
		'code': fields.selection(_code_get, 'Sequence Code',size=64, required=True),
		'active': fields.boolean('Active'),
		'prefix': fields.char('Prefix',size=64),
		'suffix': fields.char('Suffix',size=64),
		'number_next': fields.integer('Next Number', required=True),
		'number_increment': fields.integer('Increment Number', required=True),
		'padding' : fields.integer('Number padding', required=True),
	}
	_defaults = {
		'active': lambda *a: True,
		'number_increment': lambda *a: 1,
		'number_next': lambda *a: 1,
		'padding' : lambda *a : 0,
	}

	def _process(self, s):
		return (s or '') % {'year':time.strftime('%Y'), 'month': time.strftime('%m'), 'day':time.strftime('%d')}

	def get_id(self, cr, uid, sequence_id, test='id=%d'):
		cr.execute('lock table ir_sequence')
		cr.execute('select id,number_next,number_increment,prefix,suffix,padding from ir_sequence where '+test+' and active=True', (sequence_id,))
		res = cr.dictfetchone()
		if res:
			cr.execute('update ir_sequence set number_next=number_next+number_increment where id=%d and active=True', (res['id'],))
			if res['number_next']:
				return self._process(res['prefix']) + '%%0%sd' % res['padding'] % res['number_next'] + self._process(res['suffix'])
			else:
				return self._process(res['prefix']) + self._process(res['suffix'])
		return False

	def get(self, cr, uid, code):
		return self.get_id(cr, uid, code, test='code=%s')
ir_sequence()


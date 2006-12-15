##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import time
from osv import fields,osv

class board(osv.osv):
	_name = 'board.board'
	def create(self, cr, user, vals, context={}):
		return False
	def copy(self, cr, uid, id, default=None, context={}):
		return False
	_columns = {
		'name': fields.char('Board', size=64),
	}
board()


class board_note_type(osv.osv):
	_name = 'board.note.type'
	_columns = {
		'name': fields.char('Note Type', size=64, required=True),
	}
board_note_type()

def _type_get(self, cr, uid, context={}):
	obj = self.pool.get('board.note.type')
	ids = obj.search(cr, uid, [])
	res = obj.read(cr, uid, ids, ['name'], context)
	res = [(r['name'], r['name']) for r in res]
	return res

class board_note(osv.osv):
	_name = 'board.note'
	_columns = {
		'name': fields.char('Subject', size=128, required=True),
		'note': fields.text('Note'),
		'user_id': fields.many2one('res.users', 'Author', size=64),
		'date': fields.date('Date', size=64, required=True),
		'type': fields.char('Note type', size=64),
		'type': fields.selection(_type_get, 'Note type', size=64),
	}
	_defaults = {
		'user_id': lambda object,cr,uid,context: uid,
		'date': lambda object,cr,uid,context: time.strftime('%Y-%m-%d'),
	}
board_note()

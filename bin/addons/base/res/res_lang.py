##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields, osv

class lang(osv.osv):
	_name = "res.lang"
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'code': fields.char('Code', size=5, required=True),
		'translatable': fields.boolean('Translatable'),
		'active': fields.boolean('Active'),
		'direction': fields.selection([('ltr', 'Left-to-right'), ('rtl', 'Right-to-left')], 'Direction',resuired=True),
	}
	_defaults = {
		'active': lambda *a: 1,
		'translatable': lambda *a: 0,
		'direction': lambda *a: 'ltr',
	}

lang()


##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields,osv
from xml import dom

def _check_xml(self, cr, uid, ids):
	try:
		cr.execute('select arch from ir_ui_view where id in ('+','.join(map(str,ids))+')')
		for row in cr.fetchall():
			doc = dom.minidom.parseString(row[0])
		return True
	except Exception, e:
		return False

class view(osv.osv):
	_name = 'ir.ui.view'
	_columns = {
		'name': fields.char('View Name',size=64,  required=True),
		'model': fields.char('Model', size=64, required=True),
		'priority': fields.integer('Priority', required=True),
		'type': fields.selection((('tree','Tree'),('form','Form'),('graph', 'Graph')), 'View Type', required=True),
		'arch': fields.text('View Architecture', required=True),
		'inherit_id': fields.many2one('ir.ui.view', 'Inherited View'),
		'field_parent': fields.char('Childs Field',size=64)
	}
	_defaults = {
		'arch': lambda *a: '<?xml version="1.0"?>\n<tree title="Unknwown">\n\t<field name="name"/>\n</tree>',
		'priority': lambda *a: 16
	}
	_order = "priority"
	_constraints = [
		(_check_xml, 'Invalid XML for View Architecture!', ['arch'])
	]

view()

class view_sc(osv.osv):
	_name = 'ir.ui.view_sc'
	_columns = {
		'name': fields.char('Shortcut Name', size=64, required=True),
		'res_id': fields.integer('Resource Ref.', required=True),
		'sequence': fields.integer('Sequence'),
		'user_id': fields.many2one('res.users', 'User Ref.', required=True, ondelete='cascade'),
		'resource': fields.char('Resource Name', size=64, required=True)
	}
	_order = 'sequence'
	_defaults = {
		'resource': lambda *a: 'ir.ui.menu',
	}
view_sc()

##############################################################################
#
# Copyright (c) 2005 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: project.py 1011 2005-07-26 08:11:45Z nicoe $
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

from osv import fields, osv, orm

class mrp_procurement(osv.osv):
	_name = "mrp.procurement"
	_inherit = "mrp.procurement"
	
	def action_produce_assign_service(self, cr, uid, ids, context={}):
		for procurement in self.browse(cr, uid, ids):
			self.write(cr, uid, [procurement.id], {'state':'running'})
			task_id = self.pool.get('project.task').create(cr, uid, {
				'name': procurement.name,
				'date_deadline': procurement.date_planned,
				'state': 'open',
				'planned_hours': procurement.product_qty,
				'user_id': procurement.product_id.product_manager.id,
				'notes': procurement.origin,
				'procurement_id': procurement.id
			})
		return task_id
mrp_procurement()


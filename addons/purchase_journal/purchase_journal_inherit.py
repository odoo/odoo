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

from osv import osv, fields


class purchase(osv.osv):
	_inherit="purchase.order"
	_columns = {
		'journal_id': fields.many2one('purchase_journal.purchase.journal', 'Journal'),
	}
	def action_picking_create(self, cr, uid, ids, *args):
		result = super(purchase, self).action_picking_create(cr, uid, ids, *args)
		for order in self.browse(cr, uid, ids, context={}):
			pids = [ x.id for x in (order.picking_ids or [])]
			self.pool.get('stock.picking').write(cr, uid, pids, {
				'purchase_journal_id': order.journal_id.id
			})
		return result
purchase()

class picking(osv.osv):
	_inherit="stock.picking"
	_columns = {
		'purchase_journal_id': fields.many2one('purchase_journal.purchase.journal', 'Purchase Journal', select=True),
	}
picking()

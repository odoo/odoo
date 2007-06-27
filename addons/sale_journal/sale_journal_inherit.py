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


class res_partner(osv.osv):
	_inherit = 'res.partner'
	_columns = {
		'property_invoice_type': fields.property(
		'sale_journal.invoice.type',
		type='many2one',
		relation='sale_journal.invoice.type',
		string="Invoicing Method",
		method=True,
		view_load=True,
		group_name="Accounting Properties",
		help="The type of journal used for sales and packings."),
	}
res_partner()

class picking(osv.osv):
	_inherit="stock.picking"
	_columns = {
		'journal_id': fields.many2one('sale_journal.picking.journal', 'Journal'),
		'sale_journal_id': fields.many2one('sale_journal.sale.journal', 'Sale Journal'),
		'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
	}
picking()

class sale(osv.osv):
	_inherit="sale.order"
	_columns = {
		'journal_id': fields.many2one('sale_journal.sale.journal', 'Journal'),
		'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type')
	}
	def action_ship_create(self, cr, uid, ids, *args):
		result = super(sale, self).action_ship_create(cr, uid, ids, *args)
		for order in self.browse(cr, uid, ids, context={}):
			pids = [ x.id for x in order.picking_ids]
			self.pool.get('stock.picking').write(cr, uid, pids, {
				'invoice_type_id': order.invoice_type_id.id,
				'sale_journal_id': order.journal_id.id
			})
		return result

	def onchange_partner_id(self, cr, uid, ids, part):
		result = super(sale, self).onchange_partner_id(cr, uid, ids, part)
		if part:
			itype = self.pool.get('res.partner').browse(cr, uid, part).property_invoice_type
			result['value']['invoice_type_id'] = itype and itype[0]
		return result
sale()

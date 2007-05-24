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
import netsvc
import time

class sale_journal_invoice_type(osv.osv):
	_name = 'sale_journal.invoice.type'
	_description = 'Invoice Types'
	_columns = {
		'name': fields.char('Invoice Type', size=64, required=True),
		'active': fields.boolean('Active'),
		'note': fields.text('Note'),
		'invoicing_method': fields.selection([('simple','Non grouped'),('grouped','Grouped')], 'Invoicing method', required=True),
	}
	_defaults = {
		'active': lambda *a: True,
		'invoicing_method': lambda *a:'simple'
	}
sale_journal_invoice_type()

class sale_journal(osv.osv):
	_name = 'sale_journal.sale.journal'
	_description = 'Sale Journal'
	_columns = {
		'name': fields.char('Journal', size=64, required=True),
		'code': fields.char('Code', size=16, required=True),
		'user_id': fields.many2one('res.users', 'Responsible', required=True),
		'date': fields.date('Journal date', required=True),
		'date_created': fields.date('Creation date', readonly=True, required=True),
		'date_validation': fields.date('Validation date', readonly=True),
		'sale_stats_ids': fields.one2many("sale_journal.sale.stats", "journal_id", 'Sale Stats', readonly=True),
		'state': fields.selection([
			('draft','Draft'),
			('open','Open'),
			('done','Done'),
		], 'Creation date', required=True),
		'note': fields.text('Note'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'date_created': lambda *a: time.strftime('%Y-%m-%d'),
		'user_id': lambda self,cr,uid,context: uid,
		'state': lambda self,cr,uid,context: 'draft',
	}
	def button_sale_cancel(self, cr, uid, ids, context={}):
		for id in ids:
			sale_ids = self.pool.get('sale.order').search(cr, uid, [('journal_id','=',id),('state','=','draft')])
			for saleid in sale_ids:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_validate(uid, 'sale.order', saleid, 'cancel', cr)
		return True
	def button_sale_confirm(self, cr, uid, ids, context={}):
		for id in ids:
			sale_ids = self.pool.get('sale.order').search(cr, uid, [('journal_id','=',id),('state','=','draft')])
			for saleid in sale_ids:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_validate(uid, 'sale.order', saleid, 'order_confirm', cr)
		return True

	def button_open(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'open'})
		return True
	def button_draft(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'draft'})
		return True
	def button_close(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'done', 'date_validation':time.strftime('%Y-%m-%d')})
		return True
sale_journal()

class picking_journal(osv.osv):
	_name = 'sale_journal.picking.journal'
	_description = 'Pickings Journal'
	_columns = {
		'name': fields.char('Journal', size=64, required=True),
		'code': fields.char('Code', size=16, required=True),
		'user_id': fields.many2one('res.users', 'Responsible', required=True),
		'date': fields.date('Journal date', required=True),
		'date_created': fields.date('Creation date', readonly=True, required=True),
		'date_validation': fields.date('Validation date', readonly=True),
		'picking_stats_ids': fields.one2many("sale_journal.picking.stats", "journal_id", 'Journal Stats', readonly=True),
		'state': fields.selection([
			('draft','Draft'),
			('open','Open'),
			('done','Done'),
		], 'Creation date', required=True),
		'note': fields.text('Note'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'date_created': lambda *a: time.strftime('%Y-%m-%d'),
		'user_id': lambda self,cr,uid,context: uid,
		'state': lambda self,cr,uid,context: 'draft',
	}
	def button_picking_cancel(self, cr, uid, ids, context={}):
		for id in ids:
			pick_ids = self.pool.get('stock.picking').search(cr, uid, [('journal_id','=',id)])
			for pickid in pick_ids:
				wf_service = netsvc.LocalService("workflow")
				wf_service.trg_validate(uid, 'stock.picking', pickid, 'button_cancel', cr)
		return True
	def button_open(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'open'})
		return True
	def button_draft(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'draft'})
		return True
	def button_close(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state':'done', 'date_validation':time.strftime('%Y-%m-%d')})
		return True
picking_journal()


##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: product.py 1310 2005-09-08 20:40:15Z pinky $
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
import time

class account_invoice(osv.osv):
	_inherit = 'account.invoice'
	def line_get_convert(self, cr, uid, x, part, date, context={}):
		print self
		res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context)
		res['asset_id'] = x.get('asset_id', False)
		return res
account_invoice()

class account_invoice_line(osv.osv):
	_inherit = 'account.invoice.line'
	_columns = {
		'asset_id': fields.many2one('account.asset.asset', 'Asset'),
	}
	def move_line_get_item(self, cr, uid, line, context={}):
		res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context)
		res['asset_id'] = line.asset_id.id or False
		if line.asset_id.id and (line.asset_id.state=='draft'):
			self.pool.get('account.asset.asset').validate(cr, uid, [line.asset_id.id], context)
		return res
account_invoice_line()


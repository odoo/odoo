##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
from osv import osv,fields

class account_dta(osv.osv):
	_name = "account.dta"
	_description = "DTA History"
	_columns = {
		'name': fields.binary('DTA file', readonly=True),
		'dta_line_ids': fields.one2many('account.dta.line','dta_id','DTA lines', readonly=True), 
		'note': fields.text('Creation log', readonly=True),
		'bank': fields.many2one('res.partner.bank','Bank', readonly=True,select=True),
		'date': fields.date('Creation Date', readonly=True,select=True),
		'user_id': fields.many2one('res.users','User', readonly=True, select=True),
	}
account_dta()

class account_dta_line(osv.osv):
	_name = "account.dta.line"
	_description = "DTA line"
	_columns = {
		'name' : fields.many2one('account.invoice','Invoice', required=True),
		'partner_id' : fields.many2one('res.partner','Partner'),
		'due_date' : fields.date('Due date'),
		'invoice_date' : fields.date('Invoice date'),
		'cashdisc_date' : fields.date('Cash Discount date'),
		'amount_to_pay' : fields.float('Amount to pay'),
		'amount_invoice': fields.float('Invoiced Amount'),
		'amount_cashdisc': fields.float('Cash Discount Amount'),
		'dta_id': fields.many2one('account.dta','Associated DTA', required=True, ondelete='cascade'),
		'state' : fields.selection([('draft','Draft'),('cancel','Error'),('done','Paid')],'State')
	}
	_defaults = {
		'state' : lambda *a :'draft',
	}
account_dta_line()



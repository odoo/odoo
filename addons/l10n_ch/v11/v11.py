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


class account_v11(osv.osv):
	_name = "account.v11"
	_description = "V11 History"
	_columns = {
		'name': fields.binary('V11 file', readonly=True),
		'statement_ids': fields.one2many('account.bank.statement','v11_id','Generated Bank Statement', readonly=True), 
		'note': fields.text('Import log', readonly=True),
		'journal_id': fields.many2one('account.journal','Bank Journal', readonly=True,select=True),
		'date': fields.date('Import Date', readonly=True,select=True),
		'user_id': fields.many2one('res.users','User', readonly=True, select=True),
	}
account_v11()



class account_bank_statement(osv.osv):
	_inherit = "account.bank.statement"
	_columns = {
		'v11_id':fields.many2one('account.v11','V11'),
	}
account_bank_statement()

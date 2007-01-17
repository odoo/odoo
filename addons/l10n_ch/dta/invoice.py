# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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
import netsvc
from osv import fields, osv
import ir

class account_invoice(osv.osv):
	
	_inherit = "account.invoice"
	_columns = {
		'dta_state': fields.selection([('none','None'),
									   ('2bp','To be paid'),
									   ('paid','Paid')],
									  'DTA state',readonly=True,select=True, states={'draft':[('readonly',False)]}),
		'bvr_ref_num': fields.char('Bvr Reference Number', size=64,readonly=True, states={'draft':[('readonly',False)]}),
		'partner_comment':fields.char('Partner Comment', size=112, readonly=True, states={'draft':[('readonly',False)]}),
	}

	_defaults = {
		'dta_state': lambda *a: 'none',
	}

	def _check_bvr(self, cr, uid, ids):
		return True
	
	_constraints = [
		(_check_bvr, 'Error ! Invalid Bvr Number.', ['bvr_ref_num'])
	]

	
account_invoice()


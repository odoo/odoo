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

from tools.misc import currency

#from _common import rounding

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class res_currency(osv.osv):
	_name = "res.currency"
	_description = "Currency"
	_columns = {
		'name': fields.char('Currency', size=32, required=True),
		'code': fields.char('Code', size=3),
		'date': fields.date('Last rate update', readonly=True),
		'rate': fields.float('Relative Change rate',digits=(12,6)),
		#'digits': fields.integer('Displayed Digits'),
		'accuracy': fields.integer('Computational Accuracy'),
		'rounding': fields.float('Rounding factor'),
		'active': fields.boolean('Active'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'active': lambda *a: 1,
	}
	_order = "code"

	def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount):
		if to_currency_id==from_currency_id:
			return from_amount
		[from_currency]=self.read(cr, uid, [from_currency_id])
		[to_currency] = self.read(cr, uid, [to_currency_id])
		return currency(from_amount * from_currency['rate']/to_currency['rate'], to_currency['accuracy'], to_currency['rounding'])
					
			
res_currency()


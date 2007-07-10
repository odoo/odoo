##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

import ir
from osv import osv
from report import report_sxw
import pooler

class report_rappel(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(report_rappel, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time' : time,
			'adr_get' : self._adr_get,
			'getLines' : self._lines_get,
		})

	def _adr_get(self, partner, type):
		res_partner = pooler.get_pool(self.cr.dbname).get('res.partner')
		res_partner_address = pooler.get_pool(self.cr.dbname).get('res.partner.address')
		addresses = res_partner.address_get(self.cr, self.uid, [partner.id], [type])
		adr_id = addresses and addresses[type] or False
		return adr_id and res_partner_address.read(self.cr, self.uid, [adr_id])[0] or False

	def _lines_get(self, partner):
		part = pooler.get_pool(self.cr.dbname).get('res.partner')
		acc = partner.property_account_receivable[0]
		moveline_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
		movelines = moveline_obj.search(self.cr, self.uid, [('partner_id','=',partner.id), ('account_id','=',acc), ('state','=','valid'), ('date_maturity', '=', False)])
		movelines += moveline_obj.search(self.cr, self.uid, [('partner_id','=',partner.id), ('account_id','=',acc), ('state','=','valid'), ('date_maturity', '<=', time.strftime('%Y-%m-%d'))])
		movelines = moveline_obj.read(self.cr, self.uid, movelines)
		return movelines

report_sxw.report_sxw('report.account.rappel', 'res.partner', 'addons/account/report/rappel.rml',parser=report_rappel)


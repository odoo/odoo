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
from report import report_sxw

class account_invoice_bvr(report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context):
		super(account_invoice_bvr, self).__init__(cr, uid, name, context)
		self.localcontext.update({
			'time': time,
			'user':self.pool.get("res.users").browse(cr,uid,uid),
			'mod10r': self._mod10r,
			'_space': self._space,
			'_get_ref': self._get_ref,
		})

	def _space(self,nbr, nbrspc=5):
		res = ''
		for i in range(len(nbr)):
			res = res + nbr[i]
			if not (i-1) % nbrspc:
				res = res + ' '
		return res

	def _get_ref(self, o):
		res = ''
		if o.bank_id.bank_code:
			res = o.bank_id.bank_code
		return self._mod10r(res+o.number.rjust(26-len(res), '0'))

	def _mod10r(self,nbr):
		"""
		Input arg : account or invoice number
		Output return: the same number completed with the recursive mod10
		key
		"""

		codec=[0,9,4,6,8,2,7,1,3,5]
		report = 0
		result=""
		for chiffre in nbr:
			
			if not chiffre.isdigit():
				continue
			
			report = codec[ (int(chiffre) +report) % 10 ] 
			result += chiffre
		return result + str((10-report) % 10)

report_sxw.report_sxw(
	'report.l10n_ch.bvr',
	'account.invoice',
	'addons/l10n_ch/bvr/report/bvr.rml',
	parser=account_invoice_bvr,
	header=False)

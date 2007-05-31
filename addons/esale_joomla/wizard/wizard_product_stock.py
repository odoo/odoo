##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
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


import ir
import time
import os
import netsvc
import xmlrpclib
import pooler

import wizard
from osv import osv

_export_form = '''<?xml version="1.0"?>
<form string="Initial import" />
'''

_export_fields = {}

_export_done_form = '''<?xml version="1.0"?>
<form string="Initial import">
<separator string="Stock succesfully updated" colspan="4" />
</form>'''

_export_done_fields = {}

def _do_export(self, cr, uid, data, context):
	self.pool = pooler.get_pool(cr.dbname)
	ids = self.pool.get('esale_joomla.web').search(cr, uid, [])
	for website in self.pool.get('esale_joomla.web').browse(cr, uid, ids):
		server = xmlrpclib.ServerProxy("%s/tinyerp-synchro.php" % website.url)
		for osc_product in website.product_ids:
			if osc_product.esale_joomla_id:
				webproduct={
					'esale_joomla_id': osc_product.esale_joomla_id,
					'quantity': pooler.get_pool(cr.dbname).get('product.product')._product_virtual_available(cr, uid, [osc_product.product_id.id], '', False, {'shop':website.shop_id.id})[osc_product.product_id.id],
				}
			osc_id=server.set_product_stock(webproduct)
	return {}

class wiz_esale_joomla_stocks(wizard.interface):

	states = {
		'init': {
			'actions': [_do_export],
			'result': { 'type': 'form', 'arch': _export_done_form, 'fields': _export_done_fields, 'state': [('end', 'End')]}
		}
	}


wiz_esale_joomla_stocks('esale_joomla.stocks');

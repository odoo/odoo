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

import wizard

sale_form = """<?xml version="1.0"?>
<form string="Product Price">
  <field name="product_id"/>
  <field name="price_standard"/>
  <field name="price_pmp"/>
</form>"""

sale_fields = {
	'product_id' : {'string':'Product', 'type':'many2one', 'relation':'product.product'},
	'price_standard' : {'string':"Standard Price", 'type':'float'},
	'price_standard' : {'string':"Average Price", 'type':'float'},
}

#FIXME: this doesn't do anything...
def _price_calc(self, cr, uid, data, context):
	return {}

class product_price_calc(wizard.interface):
	states = {
		'init' : {
			'actions' : [_price_calc],
			'result' : {'type':'form', 'arch':sale_form, 'fields':sale_fields, 'state':[('end', 'Cancel')]}
		}
	}
product_price_calc('product.price_calc')

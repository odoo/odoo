##############################################################################
#
# Copyright (c) 2005 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: product_expiry.py 2103 2006-01-11 21:01:14Z pinky $
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

from osv import fields,osv

class product_product(osv.osv):
	_inherit = 'product.product'
	_name = 'product.product'
	_columns = {
		'manufacturer' : fields.many2one('res.partner', 'Manufacturer'),
		'manufacturer_pname' : fields.char('Manufacturer product name', size=64),
		'manufacturer_pref' : fields.char('Manufacturer product code', size=64),
		'attribute_ids': fields.one2many('product.electronic.attribute', 'product_id', 'Attributes'),
	}
product_product()

class product_attribute(osv.osv):
	_name = "product.electronic.attribute"
	_description = "Product attributes"
	_columns = {
		'name' : fields.char('Attribute', size=64, required=True),
		'value' : fields.char('Value', size=64),
		'product_id': fields.many2one('product.product', 'Product', ondelete='cascade'),
	}
product_attribute()



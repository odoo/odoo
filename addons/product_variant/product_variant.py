##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields, osv

#
# Dimensions Definition
#
class product_variant_dimension_type(osv.osv):
	_name = "product.variant.dimension.type"
	_description = "Dimension Type"
	_columns = {
		'name' : fields.char('Dimension', size=64),
		'sequence' : fields.integer('Sequence'),
		'value_ids' : fields.one2many('product.variant.dimension.value', 'Dimension Values'),
	}
	_order = "sequence, name"
product_variant_dimension_type()

class product_variant_dimension_value(osv.osv):
	_name = "product.variant.dimension.value"
	_description = "Dimension Type"
	_columns = {
		'name' : fields.char('Dimension Value', size=64),
		'sequence' : fields.integer('Sequence'),
		'price_extra' : fields.float('Dimension Values', size=64),
		'price_margin' : fields.float('Dimension Values', size=64),
		'dimension_id' : fields.many2one('product.product.dimension.type', 'Dimension', required=True),
	}
	_order = "sequence, name"
product_variant_dimension_value()

#
# Dimensions Definition
#

class product_product(osv.osv):
	_name = "product.product"
	_inherit = "product.product"

	def _variant_name_get(self, cr, uid, ids, name, arg, context={}):
		res = {}
		for p in self.browse(cr, uid, ids, context):
			r = map(lambda dim: (dim.dimension_id.name or '')+'/'+(dim.name or '-'), p.dimension_ids)
			res[p.id] = ','.join(r)
		return res

	_columns = {
		'dimension_ids': fields.many2many('product.variant.dimension.value', 'product_product_dimension_rel', 'product_id','dimension_id', 'Dimensions'),
		#
		# TODO: compute price_extra and _margin based on variants
		#
		# 'price_extra': fields.function('Price Extra'),
		# 'price_margin': fields.function('Price Margin'),
		#
		'variants': fields.function(_variant_name_get, method=True, type='char', string='Variants'),
	}
product_product()



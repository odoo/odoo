# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2014 Marcos Organizador de Negocios- Eneldo Serrata - http://marcos.do
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################
from openerp.osv import fields, osv

class product_category(osv.osv):
    _inherit = "product.category"

    def on_change_parent_id(self, cr, uid, ids, parent_id, context=None):
        parent_category = self.browse(cr, uid, parent_id)
        if parent_category.property_stock_account_input_categ:
            property_stock_account_input_categ = parent_category.property_stock_account_input_categ.id
            property_stock_account_output_categ = parent_category.property_stock_account_output_categ.id
            property_stock_valuation_account_id = parent_category.property_stock_valuation_account_id.id

            return {"value": {'property_stock_account_input_categ': property_stock_account_input_categ,
                              'property_stock_account_output_categ': property_stock_account_output_categ,
                              'property_stock_valuation_account_id': property_stock_valuation_account_id}}
        return {"value": {}}

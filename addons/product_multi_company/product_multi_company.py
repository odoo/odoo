# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from osv import osv, fields

class product_template(osv.osv):
    _inherit = "product.template"
    _columns={
        'list_price': fields.property('product.template',
            type='float',
            string='Public Price',
            method=True,
            view_load=True,
            required=True, size=64),
        'standard_price': fields.property('product.template',
            type='float',
            string='Standard Price',
            method=True,
            view_load=True,
            required=True, size=64,
            help="Product's cost for accounting stock valuation. It is the base price for the supplier price."),
        }
product_template()

class pricelist_partnerinfo(osv.osv):
    _inherit = 'pricelist.partnerinfo' 
    _columns = {
        'price': fields.property('pricelist.partnerinfo',
            type='float',
            string='Seller Price',
            method=True,
            view_load=True,
            required=True, size=64,
            help="This price will be considered as a price for the supplier UoM if any or the default Unit of Measure of the product otherwise"),
    }
pricelist_partnerinfo()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
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

from osv import fields, osv
from service import web_services
import time
import wizard
import pooler

class product_price_list(osv.osv_memory):
    _name = "product.price.list"
    _description = "Product Price List"

    _columns = {
        'price_list': fields.many2one('product.pricelist', 'PriceList', required=True), 
        'qty1':fields.integer('Quantity-1'),
	'qty2':fields.integer('Quantity-2'),
        'qty3':fields.integer('Quantity-3'),
        'qty4':fields.integer('Quantity-4'),
        'qty5':fields.integer('Quantity-5'),
}

    _defaults = {
        'qty1': lambda *a:'0',
	'qty2': lambda * a:'0',
	'qty3': lambda *a:'0',
	'qty4': lambda *a:'0',
	'qty5': lambda *a:'0',
     }
product_price_list()


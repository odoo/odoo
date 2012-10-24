# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import addons
import tools
import pytz
import time
from osv import osv, fields
from datetime import datetime, timedelta

class lunch_product(osv.Model):
    """ lunch product """
    _name = 'lunch.product'
    _description = 'lunch product'
    _columns = {
        'name' : fields.char('Product',required=True, size=64),
        'category_id': fields.many2one('lunch.product.category', 'Category'),
        'description': fields.text('Description', size=256, required=False),
        'price': fields.float('Price', digits=(16,2)),
        'active': fields.boolean('Active'), #If this product isn't offered anymore, the active boolean is set to false. This will allow to keep trace of previous orders and cashmoves.
        'supplier' : fields.many2one('res.partner','Supplier',required=True, domain=[('supplier_lunch','=',True)]), 
    }

class lunch_product_category(osv.Model):
    """ lunch product category """
    _name = 'lunch.product.category'
    _description = 'lunch product category'
    _columns = {
        'name' : fields.char('Category', required=True, size=64), #such as PIZZA, SANDWICH, PASTA, CHINESE, BURGER, ...
    }
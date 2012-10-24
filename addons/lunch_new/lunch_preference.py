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

class lunch_preference(osv.Model):
    _name = 'lunch.preference'
    _description= "user preferences"

    def onclick_preference(self,cr,uid,ids,context=None):
        print cr
        print uid
        print ids
        print context
        print self.pool.get('lunch.preference').browse(cr,uid,ids,context)[0]['product_name']
        return True

    _columns = {
        'date' : fields.date('Date', required=True,readonly=True),
        'color': fields.integer('Color'),
        'user_id' : fields.many2one('res.users','User Name',required=True,readonly=True),
        'product' : fields.many2one('lunch.product','Product',required=True),
        'product_name' : fields.char('Product name',size=64),
        'note' : fields.text('Note',size=256,required=False),
        'price' : fields.float('Price',digits=(16,2)),
    }

    _defaults = {      
        'color': 1,
    }
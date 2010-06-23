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
from tools.misc import UpdateableStr, UpdateableDict
from tools.translate import _
import netsvc
import pooler
import time
import datetime, time
import wizard

class stock_production_lot(osv.osv):
    _inherit = "stock.production.lot"
    def create(self, cr, uid, vals, context={}):
        new_id = super(stock_production_lot, self).create(cr, uid, vals, context=context)
        prodlot_obj = self.pool.get('stock.production.lot')
        prod = prodlot_obj.browse(cr, uid, new_id, context=context)
        res = {}
        current_date = time.strftime('%Y-%m-%d %H:%M:%S')
        if not prod.life_date:
            date_life = (datetime.datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=prod.product_id.life_time))
            res['life_date'] = date_life.strftime('%Y-%m-%d')
        if not prod.use_date:
            date_use = (datetime.datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=prod.product_id.use_time))
            res['use_date'] = date_use.strftime('%Y-%m-%d')
        if not prod.removal_date:
            date_removal = (datetime.datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=prod.product_id.removal_time))
            res['removal_date'] = date_removal.strftime('%Y-%m-%d')
        if not prod.alert_date:
            date_alert = (datetime.datetime.strptime(current_date, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=prod.product_id.alert_time))
            res['alert_date'] = date_alert.strftime('%Y-%m-%d')
        prodlot_obj.write(cr, uid, [prod.id], res)
        return new_id
stock_production_lot()

class stock_move_split_lines_exist(osv.osv_memory):
    _inherit = "stock.move.split.lines"
    _columns = {
        'date': fields.date('Expiry Date'),
    }
    # TODO: use this date instead of default one
    def on_change_product(self, cr, uid, ids, product_id):
        if not product_id:
            return {'value':{'date': False}}
        day_life = self.pool.get('product.product').browse(cr, uid, product_id).life_time
        date_life = (datetime.datetime.now() + datetime.timedelta(days=day_life))
        return {'value':
            {'date': date_life.strftime('%Y-%m-%d')}
        }
stock_move_split_lines_exist()

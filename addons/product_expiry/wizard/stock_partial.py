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
import datetime
import wizard

class stock_partial_lot_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    _name = "stock.partial.picking"
    _description = "Partial Picking"

    def do_partial(self, cr, uid, ids, context):
        res = super(stock_partial_lot_picking, self).do_partial(cr, uid, ids, context=context)
        prodlot_obj = self.pool.get('stock.production.lot')
        pick_obj = self.pool.get('stock.picking')
        picking_ids = context.get('active_ids', False)
        partial = self.browse(cr, uid, ids[0], context)
        for pick in pick_obj.browse(cr, uid, picking_ids):
            for m in pick.move_lines:
                for pick in pick_obj.browse(cr, uid, picking_ids):
                        for m in pick.move_lines:
                            res = {}
                            if (pick.type == 'in') and m.prodlot_id:
                                if not m.prodlot_id.life_date:
                                    date_life = (datetime.datetime.strptime(partial.date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=m.product_id.life_time))
                                    res['life_date'] = date_life.strftime('%Y-%m-%d')
                                if not m.prodlot_id.use_date:
                                    date_use = (datetime.datetime.strptime(partial.date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=m.product_id.use_time))
                                    res['use_date'] = date_use.strftime('%Y-%m-%d')
                                if not m.prodlot_id.removal_date:
                                    date_removal = (datetime.datetime.strptime(partial.date, '%Y-%m-%d %H:%M:%S')  + datetime.timedelta(days=m.product_id.removal_time))
                                    res['removal_date'] = date_removal.strftime('%Y-%m-%d')
                                if not m.prodlot_id.alert_date:
                                    date_alert = (datetime.datetime.strptime(partial.date, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=m.product_id.alert_time))
                                    res['alert_date'] = date_alert.strftime('%Y-%m-%d')
                                prodlot_obj.write(cr, uid, [m.prodlot_id.id], res)
        return res
stock_partial_lot_picking()

class stock_move_split_lines_exist(osv.osv_memory):
    _name = "stock.move.split.lines.exist"
    _inherit = "stock.move.split.lines.exist"
    _columns = {
        'date': fields.date('Date'),
    }
    def on_change_product(self, cr, uid, ids, product_id):
        if not product_id:
            return {'value':{'date': False}}
        day_life = self.pool.get('product.product').browse(cr, uid, product_id).life_time
        date_life = (datetime.datetime.now() + datetime.timedelta(days=day_life))
        return {'value':{'date': date_life.strftime('%Y-%m-%d')
}}


stock_move_split_lines_exist()

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

from osv import fields,osv
import tools
import ir
import pooler
from mx import DateTime
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta

class stock_avg_consommation(osv.osv):
    _name = "stock.avg.consommation"
    _inherit="product.product"

    def _compute_avg_consommation(self, cr, uid, ids, fields, args, context={}):
        print  ids, fields, args, context
        date_str=False
        from_date=context.get('from_date',False)
        to_date=context.get('to_date',False)

        if from_date and to_date:
            date_str="date_planned>='%s' and date_planned<='%s'"%(from_date,to_date)
        elif from_date:
            date_str="date_planned>='%s'"%(from_date)
        elif to_date:
            date_str="date_planned<='%s'"%(to_date)

        date_object_to = to_date and  datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S') or datetime.now()
        date_object_from = from_date and datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')  or (datetime.now() + relativedelta(days=-30))
        dd = date_object_to - date_object_from
        total_days=dd.days+1
        if not from_date and not to_date:
            date_str="date_planned>='%s' and date_planned<='%s'"%(date_object_from.strftime('%Y-%m-%d 00:00:00'), date_object_to.strftime('%Y-%m-%d 23:59:59'))
        elif not from_date:
            date_str="date_planned>='%s'"%(date_object_from.strftime('%Y-%m-%d 00:00:00'))
        elif not to_date:
            date_str="date_planned<='%s'"%(date_object_to.strftime('%Y-%m-%d 23:59:59'))
        res={}
        for line_id in ids:
            res[line_id] = False
        location_ids = []

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = self.pool.get('stock.location').search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
            for w in self.pool.get('stock.warehouse').browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = self.pool.get('stock.location').search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids
        else:
            location_ids = location_ids



        #sql = """select product_id,sum(product_qty) from stock_move sm,stock_picking sp where sm.picking_id=sp.id and sp.type in ('out','delivery') and %s and  location_id <> ANY(%s) and location_dest_id =ANY(%s) group by product_id""" % (date_str, location_ids, location_ids)
        sql = """select product_id,sum(product_qty) from stock_move sm,stock_picking sp where sm.picking_id=sp.id and sp.type in ('out','delivery') and """+date_str+""" and  sm.location_id not in %s and sm.location_dest_id in %s group by product_id"""
        cr.execute(sql, [tuple(location_ids), tuple(location_ids)])
        product_ids = []
        res_sum = cr.fetchall()
        for line_id, avg in res_sum:
            res[line_id] = avg/total_days
            product_ids.append(avg)
        return res

    _columns = {
        'avg_consommation':fields.function(_compute_avg_consommation,method=True, type='float', string="Average Consommation"),
    }
stock_avg_consommation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

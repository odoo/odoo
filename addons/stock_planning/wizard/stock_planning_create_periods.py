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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import osv, fields

# Object creating periods quickly
# changed that stop_date is created with hour 23:59:00 when it was 00:00:00 stop date was excluded from period
class stock_period_createlines(osv.osv_memory):
    _name = "stock.period.createlines"

    def _get_new_period_start(self, cr, uid, context=None):
        cr.execute("select max(date_stop) from stock_period")
        result = cr.fetchone()
        last_date = result and result[0] or False
        if last_date:
            period_start = datetime.strptime(last_date,"%Y-%m-%d %H:%M:%S")+ relativedelta(days=1)
            period_start = period_start - relativedelta(hours=period_start.hour, minutes=period_start.minute, seconds=period_start.second)
        else:
            period_start = datetime.today()
        return period_start.strftime('%Y-%m-%d')


    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.date('Start Date', required=True, help="Starting date for planning period."),
        'date_stop': fields.date('End Date', required=True, help="Ending date for planning period."),
        'period_ids': fields.one2many('stock.period', 'planning_id', 'Periods'),
        'period_ids': fields.many2many('stock.period', 'stock_period_createlines_stock_period_rel', 'wizard_id', 'period_id', 'Periods'),
    }
    _defaults={
        'date_start': _get_new_period_start,
    }

    def create_stock_periods(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        interval = context.get('interval',0)
        name = context.get('name','Daily')
        period_obj = self.pool.get('stock.period')
        lines = []
        for p in self.browse(cr, uid, ids, context=context):
            dt_stp = datetime.strptime(p.date_stop, '%Y-%m-%d')
            ds = datetime.strptime(p.date_start, '%Y-%m-%d')

            while ds <= dt_stp:
                if name =='Daily':
                    de = ds + relativedelta(days=(interval + 1), seconds =-1)
                    new_id = period_obj.create(cr, uid, {
                    'name': de.strftime('%Y-%m-%d'),
                    'date_start': ds.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_stop': de.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    ds = ds + relativedelta(days=(interval + 1))
                if name =="Weekly":
                    de = ds + relativedelta(days=(interval + 1), seconds =-1)
                    if dt_stp < de:
                        de = dt_stp + relativedelta(days=1, seconds =-1)
                    else:
                        de = ds + relativedelta(days=(interval + 1), seconds =-1)
                    new_name = ds.strftime('Week %W-%Y')
                    if ds.strftime('%Y') != de.strftime('%Y'):
                        new_name = ds.strftime('Week %W-%Y') + ', ' + de.strftime('Week %W-%Y')
                    new_id = period_obj.create(cr, uid, {
                    'name': new_name,
                    'date_start': ds.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_stop': de.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    ds = ds + relativedelta(days=(interval + 1))
                if name == "Monthly":
                    de = ds + relativedelta(months=interval, seconds=-1)
                    if dt_stp < de:
                        de = dt_stp + relativedelta(days=1, seconds =-1)
                    else:
                        de = ds + relativedelta(months=interval, seconds=-1)
                    new_name = ds.strftime('%Y/%m')
                    if ds.strftime('%m') != de.strftime('%m'):
                        new_name = ds.strftime('%Y/%m') + '-' + de.strftime('%Y/%m')
                    new_id =period_obj.create(cr, uid, {
                    'name': new_name, 
                    'date_start': ds.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_stop': de.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    ds = ds + relativedelta(months=interval)
                lines.append(new_id)

        return {
            'domain': "[('id','in', ["+','.join(map(str, lines))+"])]",
            'view_type': 'form',
            "view_mode": 'tree, form',
            'res_model': 'stock.period',
            'type': 'ir.actions.act_window',
        }

stock_period_createlines()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

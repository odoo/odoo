# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: partner.py 1007 2005-07-25 13:18:09Z kayhman $
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

from osv import fields,osv
import pooler
from tools import config
import time

class product_product(osv.osv):
    _inherit = "product.product"
    
    def _get_date(self, cr, uid, ids, field_names, arg, context):
        res = {}
        mapping = {
                   'date_start' : '%Y-01-01',
                   'date_stop' : '%Y-12-31',
                   }
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            fmt = ' , '.join(map(lambda x: mapping[x], field_names))
            date = context.get(field_names[0],time.strftime(fmt))
            res[val.id][field_names[0]] = date
        return res


    def _get_invoice_state(self, cr, uid, ids, field_names, arg, context):
        res = {}
        state=  context.get('invoice_state', 'open')
        for val in self.browse(cr, uid, ids):
            res[val.id] = state
        return res

    def get_avg_price_margin(self, cr, uid, ids, field_names, arg, context):
        res = {}
        mapping = {
                   'sale_avg_price' : 'out_invoice',
                   'purchase_avg_price' : 'in_invoice',
                   }
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            map_val = ' , '.join(map(lambda x: mapping[x], field_names))
            avg=0.0
            cr.execute("select avg(l.price_unit) from account_invoice_line l left join account_invoice i on (l.invoice_id = i.id) where l.product_id = %s AND i.type= %s" , (val.id,map_val,))
            avg = cr.fetchall()[0][0]
            if not avg:
                avg=0.0
            res[val.id][field_names[0]] = avg
        return res
    
    def _get_num_invoiced(self, cr, uid, ids, field_names, arg, context):
        res = {}
        mapping = {
                   'sale_num_invoiced' : 'out_invoice',
                   'purchase_num_invoiced' : 'in_invoice',
                   }
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            map_val = ' , '.join(map(lambda x: mapping[x], field_names))
            avg=0.0
            cr.execute("select sum(l.quantity) from account_invoice_line l left join account_invoice i on (l.invoice_id = i.id) where l.product_id = %s AND i.state not in ('draft','cancel') AND i.type= %s" , (val.id,map_val,))
            avg = cr.fetchall()[0][0]
            res[val.id][field_names[0]] = avg
        return res
    
    def _get_expected(self, cr, uid, ids, field_names, arg, context):
        res = {}
        mapping = {
                   'sale_expected' : 'sale_order_line',
                   'normal_cost' : 'purchase_order_line',
                   }
        mapping1 = {
                   'sale_expected' : 'product_uom_qty',
                   'normal_cost' : 'product_qty',
                   }
        
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            map_val = ' , '.join(map(lambda x: mapping1[x], field_names))
            cr.execute("select sum(l."+map_val +" * l.price_unit) from " +\
            ' , '.join(map(lambda x: mapping[x], field_names)) + " l where l.product_id = %s " , (val.id,))
            ret = cr.fetchall()[0][0]
            if not ret:
                ret=0.0
            res[val.id][field_names[0]] = ret
        return res
    
    
    def _get_turnover(self, cr, uid, ids, field_names, arg, context):
        res = {}
        mapping = {
                   'turnover' : 'out_invoice',
                   'total_cost' : 'in_invoice',
                   }
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            map_val = ' , '.join(map(lambda x: mapping[x], field_names))
            cr.execute("select sum(l.quantity * l.price_unit) from account_invoice_line l left join account_invoice i on (l.invoice_id = i.id) where l.product_id = %s AND i.state not in ('draft','cancel') AND i.type= %s " , (val.id,map_val))
            turnover = cr.fetchall()[0][0]
            res[val.id][field_names[0]]= turnover
        return res
    
    def _get_gap(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            if field_names[0] == 'sales_gap' :
                res[val.id][field_names[0]] = val.sale_expected - val.turnover
            elif field_names[0] == 'purchase_gap' :
                res[val.id][field_names[0]] = val.normal_cost - val.total_cost
        return res
    
    
    def _get_total_margin(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            mapping = {
                   'total_margin' : val.turnover - val.total_cost,
                   'expected_margin' : val.sale_expected - val.normal_cost,
                   }
            res[val.id] = {}
            res[val.id][field_names[0]] = mapping[field_names[0]]
        return res
    
    def _get_total_margin_rate(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            if not val.turnover:
                val.turnover = 1
            if not val.sale_expected: 
                val.sale_expected=1
            mapping = {
                   'total_margin_rate' : (val.total_margin * 100 ) / val.turnover ,
                   'expected_margin_rate' : (val.expected_margin * 100 ) / val.sale_expected,
                   }
            res[val.id] = {}
            res[val.id][field_names[0]] = mapping[field_names[0]]
        return res
    
    _columns = {
        'date_start': fields.function(_get_date, method=True, type='date', string='Start Date', multi='date_start'),
        'date_stop': fields.function(_get_date, method=True, type='date', string='Stop Date', multi='date_stop'),
        'invoice_state': fields.function(_get_invoice_state, method=True, type='char', string='Invoice State'),
#        'invoice_state': fields.selection(_get_invoice_state, string= 'Invoice State'),# readonly=True),
        'sale_avg_price' : fields.function(get_avg_price_margin, method=True, type='float', string='Avg. Unit Price', multi='sale_avg_price'),
        'purchase_avg_price' : fields.function(get_avg_price_margin, method=True, type='float', string='Avg. Unit Price', multi='purchase_avg_price'),
        'sale_num_invoiced' : fields.function(_get_num_invoiced, method=True, type='float', string='# Invoiced', multi='sale_num_invoiced'),
        'purchase_num_invoiced' : fields.function(_get_num_invoiced, method=True, type='float', string='# Invoiced', multi='purchase_num_invoiced'),
        'sales_gap' : fields.function(_get_gap, method=True, type='float', string='Sales Gap', multi='sales_gap'),
        'purchase_gap' : fields.function(_get_gap, method=True, type='float', string='Purchase Gap', multi='purchase_gap'),
        'turnover' : fields.function(_get_turnover, method=True, type='float', string='Turnover' ,multi='turnover'),
        'total_cost'  : fields.function(_get_turnover, method=True, type='float', string='Total Cost', multi='total_cost'),
        'sale_expected' :  fields.function(_get_expected, method=True, type='float', string='Expected Sale', multi='sale_expected'),
        'normal_cost'  : fields.function(_get_expected, method=True, type='float', string='Normal Cost', multi='normal_cost'),
        'total_margin' : fields.function(_get_total_margin, method=True, type='float', string='Total Margin', multi='total_margin'),
        'expected_margin' : fields.function(_get_total_margin, method=True, type='float', string='Expected Margin', multi='expected_margin'),
        'total_margin_rate' : fields.function(_get_total_margin_rate, method=True, type='float', string='Total Margin (%)', multi='total_margin_rate'),
        'expected_margin_rate' : fields.function(_get_total_margin_rate, method=True, type='float', string='Expected Margin (%)', multi='expected_margin_rate'),
    }
    
product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


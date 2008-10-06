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
    
    
    def _product_margin(self, cr, uid, ids, field_names, arg, context):
        res = {}               
        for val in self.browse(cr, uid, ids,context=context):
            res[val.id] = {}
            date_from=context.get('date_from', time.strftime('%Y-01-01'))	
            date_to=context.get('date_to', time.strftime('%Y-12-31'))	
            invoice_state=context.get('invoice_state', 'open')	
            if 'date_from' in field_names:
            	res[val.id]['date_from']=date_from
            if 'date_to' in field_names:
                res[val.id]['date_to']=date_to
            if 'invoice_state' in field_names:
            	res[val.id]['invoice_state']=invoice_state

            
            invoice_types=[]
            states=[]
            if invoice_state=='draft_open':
                states=['draft','open']
            elif invoice_state=='paid':
                states=['paid']
            elif invoice_state=='open':
                states=['open']
            
            if 'sale_avg_price' in field_names or 'sale_num_invoiced' in field_names or 'turnover' in field_names or 'sale_expected' in field_names:
                invoice_types=['out_invoice','in_refund']
            if 'purchase_avg_price' in field_names or 'purchase_num_invoiced' in field_names or 'total_cost' in field_names or 'normal_cost' in field_names:
                invoice_types=['in_invoice','out_refund']
            if len(invoice_types):
                sql="""
                select 
                	avg(l.price_unit) as avg_unit_price,
                	sum(l.quantity) as num_qty,
                	sum(l.quantity * l.price_unit) as total,
                	sum(sale_line.product_uom_qty * sale_line.price_unit) as sale_expected,
                	sum(purchase_line.product_qty * purchase_line.price_unit) as normal_cost	
                from account_invoice_line l
                left join account_invoice i on (l.invoice_id = i.id)
                left join sale_order_invoice_rel sale_invoice on (i.id=sale_invoice.invoice_id)
                left join sale_order sale on sale.id=sale_invoice.order_id
                left join sale_order_line  sale_line on sale.id=sale_line.order_id
                left join purchase_order purchase on purchase.invoice_id=i.id
                left join purchase_order_line purchase_line on purchase_line.order_id=purchase.id
                where l.product_id = %s and i.state in ('%s') and i.type in ('%s')            
                """%(val.id,"','".join(states),"','".join(invoice_types))                
                cr.execute(sql)
                result=cr.fetchall()[0]                
                if 'sale_avg_price' in field_names or 'sale_num_invoiced' in field_names or 'turnover' in field_names or 'sale_expected' in field_names:
                    res[val.id]['sale_avg_price']=result[0] and result[0] or 0.0
                    res[val.id]['sale_num_invoiced']=result[1] and result[1] or 0.0
                    res[val.id]['turnover']=result[2] and result[2] or 0.0
                    res[val.id]['sale_expected']=result[3] and result[3] or 0.0
                    res[val.id]['sales_gap']=res[val.id]['sale_expected']-res[val.id]['turnover']
                if 'purchase_avg_price' in field_names or 'purchase_num_invoiced' in field_names or 'total_cost' in field_names or 'normal_cost' in field_names:
                    res[val.id]['purchase_avg_price']=result[0] and result[0] or 0.0
                    res[val.id]['purchase_num_invoiced']=result[1] and result[1] or 0.0
                    res[val.id]['total_cost']=result[2] and result[2] or 0.0
                    res[val.id]['normal_cost']=result[4] and result[4] or 0.0
                    res[val.id]['purchase_gap']=res[val.id]['normal_cost']-res[val.id]['total_cost']                 
            
            if 'total_margin' in field_names:
                res[val.id]['total_margin']=val.turnover-val.total_cost
            if 'expected_margin' in field_names:
                res[val.id]['expected_margin']=val.sale_expected-val.normal_cost
            if 'total_margin_rate' in field_names:
                res[val.id]['total_margin_rate']=val.turnover and val.total_margin * 100 / val.turnover or 0.0
            if 'expected_margin_rate' in field_names:
                res[val.id]['expected_margin_rate']=val.sale_expected and val.expected_margin * 100 / val.sale_expected or 0.0 
        return res
    
    _columns = {
        'date_from': fields.function(_product_margin, method=True, type='date', string='From Date', multi=True),
        'date_to': fields.function(_product_margin, method=True, type='date', string='To Date', multi=True),
        'invoice_state': fields.function(_product_margin, method=True, type='selection', selection=[
			('paid','Paid'),
            ('open','All Open'),
            ('draft_open','Draft and Open')
			], string='Invoice State',multi=True, readonly=True),        
        'sale_avg_price' : fields.function(_product_margin, method=True, type='float', string='Avg. Unit Price', multi='sale'),
        'purchase_avg_price' : fields.function(_product_margin, method=True, type='float', string='Avg. Unit Price', multi='purchase'),
        'sale_num_invoiced' : fields.function(_product_margin, method=True, type='float', string='# Invoiced', multi='sale'),
        'purchase_num_invoiced' : fields.function(_product_margin, method=True, type='float', string='# Invoiced', multi='purchase'),
        'sales_gap' : fields.function(_product_margin, method=True, type='float', string='Sales Gap', multi='sale'),
        'purchase_gap' : fields.function(_product_margin, method=True, type='float', string='Purchase Gap', multi='purchase'),
        'turnover' : fields.function(_product_margin, method=True, type='float', string='Turnover' ,multi='sale'),
        'total_cost'  : fields.function(_product_margin, method=True, type='float', string='Total Cost', multi='purchase'),
        'sale_expected' :  fields.function(_product_margin, method=True, type='float', string='Expected Sale', multi='sale'),
        'normal_cost'  : fields.function(_product_margin, method=True, type='float', string='Normal Cost', multi='purchase'),
        'total_margin' : fields.function(_product_margin, method=True, type='float', string='Total Margin', multi='total'),
        'expected_margin' : fields.function(_product_margin, method=True, type='float', string='Expected Margin', multi='total'),
        'total_margin_rate' : fields.function(_product_margin, method=True, type='float', string='Total Margin (%)', multi='margin'),
        'expected_margin_rate' : fields.function(_product_margin, method=True, type='float', string='Expected Margin (%)', multi='margin'),
    }   
    
    
product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


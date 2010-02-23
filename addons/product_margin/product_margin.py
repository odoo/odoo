# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
import pooler
from tools import config
import time

states = {
    'paid': ('paid',),
    'open_paid': ('open','paid'),
    'draft_open_paid': ('draft','open','paid')
}

class product_product(osv.osv):
    _inherit = "product.product"


    def _product_margin(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids,context=context):
            res[val.id] = {}
            date_from=context.get('date_from', time.strftime('%Y-01-01'))
            date_to=context.get('date_to', time.strftime('%Y-12-31'))
            invoice_state=context.get('invoice_state', 'open_paid')
            if 'date_from' in field_names:
                res[val.id]['date_from']=date_from
            if 'date_to' in field_names:
                res[val.id]['date_to']=date_to
            if 'invoice_state' in field_names:
                res[val.id]['invoice_state']=invoice_state

            invoice_types=()
            if 'sale_avg_price' in field_names or 'sale_num_invoiced' in field_names or 'turnover' in field_names or 'sale_expected' in field_names:
                invoice_types=('out_invoice','in_refund')
            if 'purchase_avg_price' in field_names or 'purchase_num_invoiced' in field_names or 'total_cost' in field_names or 'normal_cost' in field_names:
                invoice_types=('in_invoice','out_refund')

            if invoice_types:
                sql="""
                select
                    avg(l.price_unit) as avg_unit_price,
                    sum(l.quantity) as num_qty,
                    sum(l.quantity * l.price_unit) as total,
                    sum(l.quantity * product.list_price) as sale_expected,
                    sum(l.quantity * product.standard_price) as normal_cost
                from account_invoice_line l
                left join account_invoice i on (l.invoice_id = i.id)
                left join product_template product on (product.id=l.product_id)
                where l.product_id = %s and i.state in %s and i.type in %s and i.date_invoice>=%s and i.date_invoice<=%s
                """
                cr.execute(sql, (val.id, states[invoice_state],
                                 invoice_types, date_from, date_to))
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
            ('paid','Paid'),('open_paid','Open and Paid'),('draft_open_paid','Draft, Open and Paid')
            ], string='Invoice State',multi=True, readonly=True),
        'sale_avg_price' : fields.function(_product_margin, method=True, type='float', string='Avg. Unit Price', multi='sale',help="Avg. Price in Customer Invoices)"),
        'purchase_avg_price' : fields.function(_product_margin, method=True, type='float', string='Avg. Unit Price', multi='purchase',help="Avg. Price in Supplier Invoices "),
        'sale_num_invoiced' : fields.function(_product_margin, method=True, type='float', string='# Invoiced', multi='sale',help="Sum of Quantity in Customer Invoices"),
        'purchase_num_invoiced' : fields.function(_product_margin, method=True, type='float', string='# Invoiced', multi='purchase',help="Sum of Quantity in Supplier Invoices"),
        'sales_gap' : fields.function(_product_margin, method=True, type='float', string='Sales Gap', multi='sale',help="Excepted Sale - Turn Over"),
        'purchase_gap' : fields.function(_product_margin, method=True, type='float', string='Purchase Gap', multi='purchase',help="Normal Cost - Total Cost"),
        'turnover' : fields.function(_product_margin, method=True, type='float', string='Turnover' ,multi='sale',help="Sum of Multification of Invoice price and quantity of Customer Invoices"),
        'total_cost'  : fields.function(_product_margin, method=True, type='float', string='Total Cost', multi='purchase',help="Sum of Multification of Invoice price and quantity of Supplier Invoices "),
        'sale_expected' :  fields.function(_product_margin, method=True, type='float', string='Expected Sale', multi='sale',help="Sum of Multification of Sale Catalog price and quantity of Customer Invoices"),
        'normal_cost'  : fields.function(_product_margin, method=True, type='float', string='Normal Cost', multi='purchase',help="Sum of Multification of Cost price and quantity of Supplier Invoices"),
        'total_margin' : fields.function(_product_margin, method=True, type='float', string='Total Margin', multi='total',help="Turnorder - Total Cost"),
        'expected_margin' : fields.function(_product_margin, method=True, type='float', string='Expected Margin', multi='total',help="Excepted Sale - Normal Cost"),
        'total_margin_rate' : fields.function(_product_margin, method=True, type='float', string='Total Margin (%)', multi='margin',help="Total margin * 100 / Turnover"),
        'expected_margin_rate' : fields.function(_product_margin, method=True, type='float', string='Expected Margin (%)', multi='margin',help="Expected margin * 100 / Expected Sale"),
    }
product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


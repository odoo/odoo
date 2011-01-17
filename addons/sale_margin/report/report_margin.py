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

from osv import fields,osv
import pooler
from tools import config
import time
import tools



class report_account_invoice_product(osv.osv):
    _name = 'report.account.invoice.product'
    _auto = False
    _description = "Invoice Statistics"    
    _columns = {
        'date': fields.date('Date', readonly=True),                
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),     
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
        ],'Type', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('open','Open'),
            ('paid','Paid'),
            ('cancel','Canceled')
        ],'State', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'amount': fields.float('Amount', readonly=True),
        'cost_price': fields.float('Cost Price', readonly=True),
        'margin': fields.float('Margin', readonly=True),
        'categ_id': fields.many2one('product.category', 'Categories', readonly=True),        
        'quantity': fields.float('Quantity', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_invoice_product')        
        cr.execute("""
            create or replace view report_account_invoice_product as (
                select
                    min(l.id) as id,
                    i.create_date as date,                    
                    to_char(date_trunc('day',i.date_invoice), 'YYYY') as year,
                    to_char(date_trunc('day',i.date_invoice), 'MM') as month,
                    to_char(date_trunc('day',i.date_invoice), 'YYYY-MM-DD') as day,                    
                    i.type,
                    i.state,
                    l.product_id,
                    t.categ_id,
                    i.partner_id,
                    sum(l.quantity * l.price_unit * (1.0 - l.discount/100.0)) as amount,
                    sum(l.quantity * l.cost_price) as cost_price,
                    sum((l.quantity * l.price_unit * (1.0 - l.discount/100.0) - (l.quantity * l.cost_price))) as margin,
                    sum(l.quantity) as quantity
                from account_invoice i
                    left join account_invoice_line l on (i.id = l.invoice_id)
                    left join product_product p on (p.id = l.product_id)
                    left join product_template t on (t.id = p.product_tmpl_id)                    
                group by t.categ_id,i.partner_id,l.product_id, i.date_invoice, i.type, i.state,i.create_date
            )
        """)
report_account_invoice_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


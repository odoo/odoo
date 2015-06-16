 # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
 
from openerp.osv import fields, osv
from openerp import tools

class sale_report(osv.osv):
    _inherit = "sale.report"
    _columns = {
        'shipped': fields.boolean('Shipped', readonly=True),
        'shipped_qty_1': fields.integer('# of Shipped Lines', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',readonly=True),
        'state': fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Sale to Invoice'),
            ('progress', 'Sale Order'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')
            ], 'Order Status', readonly=True),
    }

    def _select(self):
        return  super(sale_report, self)._select() + ", s.warehouse_id as warehouse_id, s.shipped, s.shipped::integer as shipped_qty_1"

    def _group_by(self):
        return super(sale_report, self)._group_by() + ", s.warehouse_id, s.shipped"

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.osv import expression


class ReportPurchaseSale(models.Model):
    _name = 'report.purchase.sale'
    _auto = False
    _description = 'Report Purchase Sale'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    # sale_line_id = fields.Many2one('sale.order.line', readonly=True)
    # purchase_line_id = fields.Many2one('purchase.order.line', readonly=True)
    # name = fields.Char()
    sale_delivered = fields.Float()
    purchase_received = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_purchase_sale')
        query = """
CREATE or REPLACE VIEW report_purchase_sale AS (
SELECT
    row_number() OVER () as id,
    pt.id as product_id,
    sum(sol.qty_delivered) as sale_delivered,
    sum(pol.qty_received) as purchase_received
FROM
    public.product_product as pt
    INNER JOIN public.purchase_order_line AS pol on pol.product_id = pt.id AND pol.state='purchase'
    INNER JOIN public.sale_order_line AS sol on sol.product_id = pt.id AND sol.state='sale'
GROUP BY pt.id);
"""
        self.env.cr.execute(query)

    # self.env.cr.execute('''
    #           CREATE OR REPLACE VIEW %s AS (
    #           select
    #           row_number() OVER () AS id,
    #           product.id as product_id,
    #           sum(pol.product_qty) as purchased_qty,
    #           sum(sol.product_uom_qty) as sale_qty
    #           from product_product as product
    #           left join purchase_order_line as pol on pol.product_id = product.id
    #               and pol.state='purchase'
    #           left join sale_order_line as sol on sol.product_id = product.id
    #               and sol.state='sale'
    #           group by  product.id
    #           )''' % (self._table,)
    #                     )
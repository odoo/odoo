# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class VendorDelayReport(models.Model):
    _name = "vendor.delay.report"
    _description = "Vendor Delay Report"
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    date = fields.Datetime('Effective Date', readonly=True)
    qty_total = fields.Float('Total Quantity', readonly=True)
    qty_on_time = fields.Float('On-Time Quantity', readonly=True)
    on_time_rate = fields.Float('On-Time Delivery Rate', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'vendor_delay_report')
        self.env.cr.execute("""
CREATE OR replace VIEW vendor_delay_report AS(
SELECT m.id                     AS id,
       m.date                   AS date,
       m.purchase_line_id       AS purchase_line_id,
       m.product_id             AS product_id,
       Min(pc.id)               AS category_id,
       Min(po.partner_id)       AS partner_id,
       Min(m.product_qty)       AS qty_total,
       Sum(CASE
             WHEN (m.state = 'done' and pol.date_planned::date >= m.date::date) THEN (ml.qty_done / ml_uom.factor * pt_uom.factor)
             ELSE 0
           END)                 AS qty_on_time
FROM   stock_move m
       JOIN purchase_order_line pol
         ON pol.id = m.purchase_line_id
       JOIN purchase_order po
         ON po.id = pol.order_id
       JOIN product_product p
         ON p.id = m.product_id
       JOIN product_template pt
         ON pt.id = p.product_tmpl_id
       JOIN uom_uom pt_uom
         ON pt_uom.id = pt.uom_id
       JOIN product_category pc
         ON pc.id = pt.categ_id
       LEFT JOIN stock_move_line ml
         ON ml.move_id = m.id
       LEFT JOIN uom_uom ml_uom
         ON ml_uom.id = ml.product_uom_id
GROUP  BY m.id
)""")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if all('on_time_rate' not in field for field in fields):
            res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
            return res

        for field in fields:
            if 'on_time_rate' not in field:
                continue

            fields.remove(field)

            agg = field.split(':')[1:]
            if agg and agg[0] != 'sum':
                raise NotImplementedError('Aggregate functions other than \':sum\' are not allowed.')

            qty_total = field.replace('on_time_rate', 'qty_total')
            if qty_total not in fields:
                fields.append(qty_total)
            qty_on_time = field.replace('on_time_rate', 'qty_on_time')
            if qty_on_time not in fields:
                fields.append(qty_on_time)
            break

        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        for group in res:
            if group['qty_total'] == 0:
                on_time_rate = 100
            else:
                on_time_rate = group['qty_on_time'] / group['qty_total'] * 100
            group.update({'on_time_rate': on_time_rate})

        return res

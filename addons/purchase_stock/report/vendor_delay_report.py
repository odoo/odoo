# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.osv import expression
from odoo.tools import SQL


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
        # Important: Avoid adding computed fields to the report unless you're
        # sure the values will be flushed in time (eg after an `unlink()`).
        # In absence of a `_depends`, ORM won't automatically flush them.
        self.env.cr.execute("""
CREATE OR replace VIEW vendor_delay_report AS(
SELECT pol.id                   AS id,
       Min(po.date_order)       AS date,
       pol.id                   AS purchase_line_id,
       pol.product_id           AS product_id,
       Min(pc.id)               AS category_id,
       pol.partner_id           AS partner_id,
       pol.product_uom_qty      AS qty_total,
       Least(Sum(CASE
                 WHEN (m.state = 'done'
                       AND dest.usage != 'supplier'
                       AND m.origin_returned_move_id IS NULL
                       AND pol.date_planned::date >= m.date::date)
                 THEN (ml.quantity / ml_uom.factor * pol_uom.factor)
                 ELSE 0
                  END), pol.product_qty) / pol.product_qty * pol.product_uom_qty AS qty_on_time
FROM   stock_move m
       JOIN purchase_order_line pol
         ON pol.id = m.purchase_line_id
       JOIN purchase_order po
         ON po.id = pol.order_id
       JOIN uom_uom pol_uom
         ON pol_uom.id = pol.product_uom
       JOIN stock_location dest
         ON dest.id = m.location_dest_id
       JOIN product_product p
         ON p.id = m.product_id
       JOIN product_template pt
         ON pt.id = p.product_tmpl_id
       JOIN product_category pc
         ON pc.id = pt.categ_id
       LEFT JOIN stock_move_line ml
         ON ml.move_id = m.id
       LEFT JOIN uom_uom ml_uom
         ON ml_uom.id = ml.product_uom_id
WHERE  pol.product_uom_qty > 0
        AND EXISTS (SELECT 1
                      FROM stock_move rm
                      JOIN purchase_order_line rpol
                        ON rpol.id = rm.purchase_line_id
                      JOIN stock_location rdest
                        ON rdest.id = rm.location_dest_id
                     WHERE rpol.order_id = po.id
                       AND rm.state = 'done'
                       AND rdest.usage != 'supplier'
                       AND rm.origin_returned_move_id IS NULL)
GROUP  BY pol.id
)""")

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == 'on_time_rate:sum':
            # Make a weigthed average instead of simple average for these fields
            return SQL(
                'CASE WHEN SUM(%s) !=0 THEN SUM(%s) / SUM(%s) * 100 ELSE 100 END',
                self._field_to_sql(self._table, 'qty_total', query),
                self._field_to_sql(self._table, 'qty_on_time', query),
                self._field_to_sql(self._table, 'qty_total', query),
            )
        return super()._read_group_select(aggregate_spec, query)

    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        if 'on_time_rate:sum' in aggregates:
            having = expression.AND([having, [('qty_total:sum', '>', '0')]])
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

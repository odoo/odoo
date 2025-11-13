# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.fields import Domain
from odoo.tools import SQL


class VendorDelayReport(models.Model):
    _name = 'vendor.delay.report'
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
             WHEN (m.state = 'done' and pol.date_planned::date >= m.date::date) THEN ((ml.quantity * ml_uom.factor) / pt_uom.factor)
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
       LEFT JOIN product_category pc
         ON pc.id = pt.categ_id
       LEFT JOIN stock_move_line ml
         ON ml.move_id = m.id
       LEFT JOIN uom_uom ml_uom
         ON ml_uom.id = ml.product_uom_id
GROUP  BY m.id
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
            having = Domain.AND([having, [('qty_total:sum', '>', '0')]])
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

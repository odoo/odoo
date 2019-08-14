# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ReportStockQuantity(models.Model):
    _name = 'report.stock.quantity'
    _auto = False
    _description = 'Stock Quantity Report'

    date = fields.Date(string='Date', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    state = fields.Selection([
        ('forecast', 'Forecasted Stock'),
        ('in', 'Forecasted Receipts'),
        ('out', 'Forecasted Deliveries'),
    ], string='State', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    move_ids = fields.One2many('stock.move', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_quantity')
        query = """
CREATE or REPLACE VIEW report_stock_quantity AS (
SELECT
    m.id,
    product_id,
    CASE
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' THEN 'out'
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) THEN 'in'
    END AS state,
    date_expected::date AS date,
    CASE
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' THEN -product_qty
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) THEN product_qty
    END AS product_qty,
    m.company_id,
    CASE
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' THEN whs.id
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) THEN whd.id
    END AS warehouse_id
FROM
    stock_move m
LEFT JOIN stock_location ls on (ls.id=m.location_id)
LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
LEFT JOIN product_product pp on pp.id=m.product_id
LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
WHERE
    pt.type = 'product' AND
    product_qty != 0 AND (
    (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' OR
    ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL)) AND
    m.state NOT IN ('cancel', 'draft', 'done')
UNION
SELECT
    -q.id as id,
    product_id,
    'forecast' as state,
    date.*::date,
    quantity as product_qty,
    q.company_id,
    wh.id as warehouse_id
FROM
    GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month',
    (now() at time zone 'utc')::date + interval '3 month', '1 day'::interval) date,
    stock_quant q
LEFT JOIN stock_location l on (l.id=q.location_id)
LEFT JOIN stock_warehouse wh ON l.parent_path like concat('%/', wh.view_location_id, '/%')
WHERE
    l.usage = 'internal'
UNION
SELECT
    m.id,
    product_id,
    'forecast' as state,
    GENERATE_SERIES(
    CASE
        WHEN state = 'done' THEN (now() at time zone 'utc')::date - interval '3month'
        ELSE date_expected::date
    END,
    CASE
        WHEN state != 'done' THEN (now() at time zone 'utc')::date + interval '3 month'
        ELSE date::date - interval '1 day'
    END, '1 day'::interval)::date date,
    CASE
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' AND state = 'done' THEN product_qty
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) AND state = 'done' THEN -product_qty
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' THEN -product_qty
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) THEN product_qty
    END AS product_qty,
    m.company_id,
    CASE
        WHEN (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' THEN whs.id
        WHEN ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL) THEN whd.id
    END AS warehouse_id
FROM
    stock_move m
LEFT JOIN stock_location ls on (ls.id=m.location_id)
LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
LEFT JOIN product_product pp on pp.id=m.product_id
LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
WHERE
    pt.type = 'product' AND
    product_qty != 0 AND (
    (ls.usage = 'internal' OR ls.usage = 'transit' AND ls.company_id IS NOT NULL) AND ld.usage != 'internal' OR
    ls.usage != 'internal' AND (ld.usage = 'internal' OR ld.usage = 'transit' AND ld.company_id IS NOT NULL)) AND
    m.state NOT IN ('cancel', 'draft')
);
"""
        self.env.cr.execute(query)

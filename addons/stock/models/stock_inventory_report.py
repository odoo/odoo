# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class StockInventoryReport(models.Model):
    _name = 'stock.inventory.report'
    _description = 'Products (Inventory Report)'
    _auto = False

    location_id = fields.Many2one('stock.location', 'Location')
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    owner_id = fields.Many2one('res.partner', 'Owner')
    package_id = fields.Many2one('stock.quant.package', 'Package')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    company_id = fields.Many2one('res.company', 'Company')
    quantity = fields.Float('Quantity', group_operator='SUM')
    date = fields.Date(string='Date', group_operator='MAX')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'stock_inventory_report')
        query = """
CREATE or REPLACE VIEW stock_inventory_report AS (
WITH stock_inventory_report_tmp AS (
SELECT
    -MIN(q.id) as id,
    product_id,
    location_id,
    lot_id,
    owner_id,
    package_id,
    date.*::date,
    SUM(quantity) as product_qty,
    company_id
FROM
    GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month',
    (now() at time zone 'utc')::date + interval '3 month', '1 day'::interval) date,
    stock_quant q
GROUP BY
    product_id, location_id, lot_id, owner_id, package_id, date, company_id
UNION
SELECT
    MIN(ml.id),
    product_id,
    location_dest_id as location_id,
    lot_id,
    owner_id,
    package_id,
    GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month', date::date - interval '1 day', '1 day'::interval)::date date,
    SUM(-qty_done / u_pp.factor * u_pp.factor) AS product_qty,
    ml.company_id
FROM
    stock_move_line ml
LEFT JOIN uom_uom u_ml ON ml.product_uom_id = u_ml.id
LEFT JOIN product_product pp ON pp.id = ml.product_id
LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
LEFT JOIN uom_uom u_pp ON u_pp.id = pt.uom_id
WHERE
    ml.state = 'done'
GROUP BY
    product_id, location_dest_id, lot_id, owner_id, package_id, date, ml.company_id
UNION
SELECT
    MIN(ml.id),
    product_id,
    location_id,
    lot_id,
    owner_id,
    package_id,
    GENERATE_SERIES((now() at time zone 'utc')::date - interval '3month', date::date - interval '1 day', '1 day'::interval)::date date,
    SUM(qty_done / u_pp.factor * u_pp.factor) AS product_qty,
    ml.company_id
FROM
    stock_move_line ml
LEFT JOIN uom_uom u_ml ON ml.product_uom_id = u_ml.id
LEFT JOIN product_product pp ON pp.id = ml.product_id
LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
LEFT JOIN uom_uom u_pp ON u_pp.id = pt.uom_id
WHERE
    ml.state = 'done'
GROUP BY
    product_id, location_id, lot_id, owner_id, package_id, date, ml.company_id
)
SELECT
    row_number() over() AS id,
    product_id,
    location_id,
    lot_id,
    owner_id,
    package_id,
    date::date,
    SUM(product_qty) AS quantity,
    company_id
FROM
    stock_inventory_report_tmp
GROUP BY
    product_id, location_id, lot_id, owner_id, package_id, date, company_id
HAVING
    SUM(product_qty) != 0
);
"""
        self.env.cr.execute(query)

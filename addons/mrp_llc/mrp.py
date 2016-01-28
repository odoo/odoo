# -*- coding: utf-8 -*-
# See __openerp__.py file for full copyright and licensing details.

from openerp import api, fields, models


class mrp_bom_llc(models.Model):
    _name = "mrp.bom.llc"
    _description = "MRP Low Level Code"
    _auto = False
    _order = 'llc'

    llc = fields.Integer('Orderpoint LLC', readonly=True)

    _depends = {
        'mrp.bom': ['product_id', 'type'],
        'mrp.bom.line': ['product_id', 'bom_id'],
    }

    def init(self, cr):
        cr.execute("""create or replace view mrp_bom_llc as (
            with j as (
                -- if only template specified on mrp.bom, then expand list with all variants
                SELECT DISTINCT
                    COALESCE(b.product_id,p.id) AS parent_id,
                    l.product_id AS comp_id
                FROM mrp_bom_line AS l, mrp_bom AS b, product_product AS p
                WHERE b.product_tmpl_id=p.product_tmpl_id
                AND l.bom_id=b.id
            )
            SELECT *
            FROM (
                 -- build a path array
                with recursive stack(parent_id, comp_id, path) as (
                    SELECT
                        j.parent_id,
                        j.comp_id,
                        ARRAY[j.comp_id]
                    FROM j
                    WHERE j.parent_id NOT IN (SELECT comp_id FROM j)
                    UNION ALL
                    SELECT
                        j.parent_id,
                        j.comp_id,
                        path || j.comp_id
                    FROM stack AS s, j
                    WHERE j.parent_id=s.comp_id
                )
                -- use longest path for each orderpoint as llc
                SELECT
                    op.id,
                    COALESCE(MAX(ARRAY_LENGTH(path, 1)), 0) AS llc
                FROM stock_warehouse_orderpoint AS op
                LEFT JOIN stack AS s ON op.product_id=s.comp_id
                GROUP BY op.id
            ) AS res
        )""")

    @api.model
    def update_orderpoint_llc(self):
        for llc in self.env['mrp.bom.llc'].search([]):
            for op in self.env['stock.warehouse.orderpoint'].browse(llc.id):
                op.llc = llc.llc

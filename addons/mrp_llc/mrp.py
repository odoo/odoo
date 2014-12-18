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
            -------------------------------------------------------------------
            -- in order to handle phantom assemblies, need to change 2 things
            --  1. only push to the path array when type is not phantom
            --  2. finally exclude phantom-only components from the list
            -- join required tables, with expansion of templates to variants
            with j as (
                SELECT DISTINCT
                    COALESCE(b.product_id,p.id) AS parent_id,
                    l.product_id AS comp_id,
                    b.type
                FROM mrp_bom_line AS l, mrp_bom AS b, product_product AS p
                WHERE b.product_tmpl_id=p.product_tmpl_id
                AND l.bom_id=b.id
            )
            SELECT *
            FROM (
                with recursive stack(parent_id, comp_id, path, comp_phantom) as (
                    SELECT
                        j.parent_id,
                        j.comp_id,
                        CASE WHEN j.type<>'phantom' AND COALESCE('', j.type)<>'phantom' THEN
                                ARRAY[j.parent_id, j.comp_id]
                            WHEN j.type<>'phantom' AND COALESCE('', j.type)='phantom' THEN
                                ARRAY[j.parent_id]
                            WHEN j.type='phantom' AND COALESCE('', j.type)<>'phantom' THEN
                                ARRAY[j.comp_id]
                            ELSE
                                ARRAY[]::int[]
                            END,
                        CASE WHEN j.type='phantom' THEN true ELSE false END
                    FROM j
                    WHERE j.parent_id NOT IN (SELECT comp_id FROM j)
                    UNION ALL
                    SELECT
                        j.parent_id,
                        j.comp_id,
                        CASE WHEN j.type<>'phantom' THEN
                                path || j.comp_id
                            ELSE
                                path
                            END,
                        CASE WHEN j.type='phantom' THEN true ELSE false END
                    FROM stack AS s, j
                    WHERE j.parent_id=s.comp_id
                )
                SELECT
                    op.id,
                    CASE WHEN BOOL_AND(comp_phantom) THEN 0 ELSE COALESCE(MAX(ARRAY_LENGTH(path, 1))-1, 0) END AS llc
                FROM stock_warehouse_orderpoint AS op
                LEFT JOIN stack AS s ON op.product_id=s.comp_id
                GROUP BY op.id
            ) AS res
            -------------------------------------------------------------------
        )""")

    @api.model
    def update_orderpoint_llc(self):
        llc_obj = self.env['mrp.bom.llc']
        llc_ids = llc_obj.search([])
        for llc_id in llc_ids:
            for orderpoint in self.env['stock.warehouse.orderpoint'].search(
                    [('id', '=', llc_id.id)]):
                orderpoint.sequence = llc_id.llc

import time

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    manufactured_num_products = fields.Float(compute="_compute_product_margin_fields_values", string="# Manufactured Products",
        help="Sum of Quantity in Manufacturing Orders")

    def _compute_product_margin_fields_values(self):
        res = super()._compute_product_margin_fields_values()
        date_from = self.env.context.get("date_from", time.strftime("%Y-01-01"))
        date_to = self.env.context.get("date_to", time.strftime("%Y-12-31"))
        company_id = self.env.context.get("force_company", self.env.company.id)
        sqlquery = """
                    SELECT
                        cpc.product_id,
                        SUM(cpc.qty_producing) AS total_produced,
                        SUM(
                            COALESCE(
                            (
                                COALESCE(cpc.total_components_cost, 0) + COALESCE(opc.total_operation_cost, 0) - (
                                COALESCE(
                                    cpc.total_components_cost * byp.cost_share,
                                    0
                                ) + COALESCE(
                                    opc.total_operation_cost * byp.cost_share,
                                    0
                                )
                                )
                            ),
                            0
                            )
                        ) AS total_production_cost
                    FROM
                    (
                        SELECT
                            mrp.id,
                            mrp.product_id,
                            mrp.qty_producing,
                            SUM(mpc.cost_components) AS total_components_cost
                            FROM
                            mrp_production AS mrp FULL
                        JOIN(
                            SELECT
                                sm.id AS stock_move_id,
                                sm.raw_material_production_id AS raw_m_p,
                            (
                                sm.quantity * COALESCE(
                                (
                                    CASE WHEN um.prd_uom IS NULL
                                    OR um.st_uom IS NULL
                                    OR um.st_uom = um.prd_uom THEN COALESCE(
                                    NULLIF(svsp.new_standard_price, 0),
                                    NULLIF(sp.standard_price, 0),
                                    0
                                    ) WHEN um.prd_uom_category != um.st_uom_category THEN COALESCE(
                                    NULLIF(svsp.new_standard_price, 0),
                                    NULLIF(sp.standard_price, 0),
                                    0
                                    ) ELSE CASE WHEN um.st_uom IS NOT NULL THEN COALESCE(
                                    NULLIF(svsp.new_standard_price, 0),
                                    NULLIF(sp.standard_price, 0),
                                    0
                                    ) * um.prd_uom_factor / um.st_uom_factor ELSE COALESCE(
                                    NULLIF(svsp.new_standard_price, 0),
                                    NULLIF(sp.standard_price, 0),
                                    0
                                    ) * um.prd_uom_factor END END
                                ),
                                0
                                )
                            ) AS cost_components
                            FROM
                            stock_move AS sm
                            LEFT JOIN (
                                SELECT
                                    sm.id AS STOCK_MOVE_ID,
                                    CASE WHEN SUM(svl.quantity) != 0 THEN (
                                        SUM(svl.value) / SUM(svl.quantity)
                                    ) ELSE NULL END AS new_standard_price
                                FROM
                                stock_valuation_layer AS svl
                                JOIN stock_move AS sm ON svl.stock_move_id = sm.id
                                GROUP BY sm.id
                            ) AS svsp ON sm.id = svsp.stock_move_id
                            LEFT JOIN (
                                SELECT
                                    p.id AS product_id,
                                    ip.value_float AS standard_price
                                FROM
                                product_product AS p
                                JOIN ir_property AS ip ON ip.company_id = %s
                                AND NAME = 'standard_price'
                                AND res_id = CONCAT('product.product', ',', p.id)
                            ) AS sp ON sp.product_id = sm.product_id
                            LEFT JOIN (
                                SELECT
                                    sm.id AS stock_move_id,
                                    sm.product_uom AS st_uom,
                                    sm.product_id AS st_product_id,
                                    uom.category_id AS st_uom_category,
                                    uom.factor AS st_uom_factor,
                                    prd.uom_id AS prd_uom,
                                    prd.category_id AS prd_uom_category,
                                    prd.factor AS prd_uom_factor
                                FROM
                                stock_move AS sm
                                JOIN (
                                    SELECT
                                        pp.id,
                                        pp.product_tmpl_id,
                                        pt.uom_id,
                                        uom.category_id,
                                        uom.factor
                                    FROM
                                    product_product AS pp
                                    JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                                    JOIN uom_uom AS uom ON pt.uom_id = uom.id
                                ) AS prd ON prd.id = sm.product_id
                                JOIN uom_uom AS uom ON uom.id = sm.product_uom
                            ) AS um ON um.stock_move_id = sm.id
                            WHERE
                            sm.scrapped = 'false'
                        ) AS mpc ON mpc.raw_m_p = mrp.id
                        WHERE
                        mrp.state = 'done'
                        AND mrp.product_id IN %s
                        AND mrp.date_start BETWEEN %s AND %s
                        AND mrp.date_finished BETWEEN %s AND %s
                        AND mrp.company_id = %s
                        GROUP BY mrp.id
                    ) AS cpc FULL
                    JOIN (
                        SELECT
                            mrp.id,
                            sm.id AS stock_move_id,
                            sm.product_id AS byproduct_id,
                            sm.cost_share / 100 AS cost_share
                        FROM
                        mrp_production AS mrp
                        JOIN stock_move AS sm ON mrp.id = sm.production_id
                        WHERE
                        mrp.product_id != sm.product_id
                        AND sm.scrapped = 'false'
                        AND (
                            mrp.id != sm.raw_material_production_id
                            OR sm.raw_material_production_id IS NULL
                        )
                    ) AS byp ON byp.id = cpc.id FULL
                    JOIN (
                        SELECT
                            mp.id,
                            mp.product_id,
                            SUM(wo.total_expenditure) AS total_operation_cost
                        FROM
                        mrp_production AS mp
                        JOIN (
                            SELECT
                                mrp_workorder.id,
                                mrp_workorder.costs_hour,
                                mrp_workorder.production_id,
                                mrp_workcenter_productivity.workorder_id AS time_ids,
                                COALESCE(
                                    COALESCE(
                                    SUM(
                                        CASE WHEN mrp_workcenter_productivity.date_end IS NOT NULL THEN EXTRACT(
                                        EPOCH
                                        FROM
                                            (
                                            mrp_workcenter_productivity.date_end - mrp_workcenter_productivity.date_start
                                            )
                                        ) ELSE EXTRACT(
                                        EPOCH
                                        FROM
                                            (
                                            NOW() - mrp_workcenter_productivity.date_start
                                            )
                                        ) END
                                    ) / 3600,
                                    0
                                    ) * (
                                    mrp_workcenter_productivity.employee_cost + mrp_workorder.costs_hour
                                    ),
                                    0
                                ) AS total_expenditure
                            FROM
                            mrp_workorder
                            JOIN mrp_workcenter_productivity ON mrp_workcenter_productivity.workorder_id = mrp_workorder.id
                            GROUP BY
                            mrp_workorder.id,
                            mrp_workorder.costs_hour,
                            mrp_workcenter_productivity.workorder_id,
                            mrp_workcenter_productivity.employee_cost
                        ) AS wo ON wo.production_id = mp.id
                        WHERE
                        mp.product_id IN %s
                        AND mp.date_start BETWEEN %s AND %s
                        AND mp.date_finished BETWEEN %s AND %s
                        AND mp.company_id = %s
                        GROUP BY mp.id
                    ) AS opc ON opc.id = cpc.id
                    GROUP BY cpc.product_id
                """
        self.env.cr.execute(
            sqlquery,
            (
                company_id,
                tuple(self.ids),
                date_from,
                date_to,
                date_from,
                date_to,
                company_id,
                tuple(self.ids),
                date_from,
                date_to,
                date_from,
                date_to,
                company_id,
            ),
        )
        result_out = self.env.cr.fetchall()
        manufactured_prds = []
        for prodt_id, total_produced, total_production_cost in result_out:
            product = self.env["product.product"].browse(prodt_id)
            if product:
                manufactured_prds.append(prodt_id)
                res[prodt_id]["total_cost"] += total_production_cost
                res[prodt_id]["manufactured_num_products"] = total_produced
                res[prodt_id]["total_margin"] -= total_production_cost
                res[prodt_id]["total_margin_rate"] -= (res[prodt_id].get("turnover", 0.0) and total_production_cost * 100 / res[prodt_id].get("turnover", 0.0) or 0.0)
                product.update(res[prodt_id])
        for product in self:
            product_id = product.id
            if not product_id in manufactured_prds:
                res[product_id]["manufactured_num_products"] = 0
                product.update(res[product.id])
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSaleReport(models.Model):
    _inherit = "report.all.channels.sales"

    def _pos(self):
        pos_str = """
                 SELECT
                    (-1) * pol.id AS id,
                    pos.name AS name,
                    pos.partner_id AS partner_id,
                    pol.product_id AS product_id,
                    pro.product_tmpl_id AS product_tmpl_id,
                    pos.date_order AS date_order,
                    pos.user_id AS user_id,
                    pt.categ_id AS categ_id,
                    pos.company_id AS company_id,
                    ((pol.qty * pol.price_unit) * (100 - pol.discount) / 100) AS price_total,
                    pos.pricelist_id AS pricelist_id,
                    rp.country_id AS country_id,
                    (pol.qty * pol.price_unit) AS price_subtotal,
                    (pol.qty * u.factor) AS product_qty,
                    NULL AS analytic_account_id,
                    config.crm_team_id AS team_id

                FROM pos_order_line AS pol
                    JOIN pos_order pos ON (pos.id = pol.order_id)
                    LEFT JOIN pos_session session ON (session.id = pos.session_id)
                    LEFT JOIN pos_config config ON (config.id = session.config_id)
                    LEFT JOIN product_product pro ON (pol.product_id = pro.id)
                    LEFT JOIN product_template pt ON (pro.product_tmpl_id = pt.id)
                    LEFT JOIN product_category AS pc ON (pt.categ_id = pc.id)
                    LEFT JOIN res_company AS rc ON (pos.company_id = rc.id)
                    LEFT JOIN res_partner rp ON (rc.partner_id = rp.id)
                    LEFT JOIN product_uom u ON (u.id=pt.uom_id)
         """
        return pos_str

    def _from(self):
        return """(%s UNION ALL %s)""" % (self._so(), self._pos())

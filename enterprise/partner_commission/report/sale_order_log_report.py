# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class SaleOrderLogReport(models.Model):
    _inherit = 'sale.order.log.report'

    referrer_id = fields.Many2one('res.partner', 'Referrer', readonly=True)
    commission_plan_id = fields.Many2one('commission.plan', readonly=True)

    def _select(self):
        select = super()._select()
        return f"""
                {select},
                so.referrer_id AS referrer_id,
                so.commission_plan_id AS commission_plan_id
        """

    def _group_by(self):
        group_by = super()._group_by()
        return f"""
            {group_by},
            so.referrer_id,
            so.commission_plan_id
        """

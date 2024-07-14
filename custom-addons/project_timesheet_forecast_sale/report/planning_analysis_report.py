# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PlanningAnalysisReport(models.Model):
    _inherit = "planning.analysis.report"

    billable_allocated_hours = fields.Float("Billable Hours Allocated", readonly=True, help="Sum of hours allocated to shifts linked to a SOL.")
    non_billable_allocated_hours = fields.Float("Non-billable Hours Allocated", readonly=True, help="Sum of hours allocated to shifts not linked to a SOL.")

    @property
    def _table_query(self):
        return f"""
            SELECT S.*,
                (S.allocated_hours - billable_allocated_hours) AS non_billable_allocated_hours
            FROM (
                {super()._table_query}
            ) S
        """

    @api.model
    def _select(self):
        return super()._select() + """,
            CASE WHEN S.sale_line_id IS NULL THEN 0 ELSE S.allocated_hours END AS billable_allocated_hours
        """

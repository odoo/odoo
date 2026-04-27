# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PlanningAnalysisReport(models.Model):
    _inherit = "planning.analysis.report"

    project_id = fields.Many2one("project.project", string="Project", readonly=True)

    @api.model
    def _select(self):
        return super()._select() + """,
            S.project_id AS project_id
        """

    @api.model
    def _group_by(self):
        return super()._group_by() + """,
            S.project_id
        """

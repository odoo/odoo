# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    production_count = fields.Integer(related="analytic_account_id.production_count")
    workorder_count = fields.Integer(related="analytic_account_id.workorder_count")
    bom_count = fields.Integer(related="analytic_account_id.bom_count")

    def action_view_mrp_production(self):
        self.ensure_one()
        return self.analytic_account_id.action_view_mrp_production()

    def action_view_mrp_bom(self):
        self.ensure_one()
        return self.analytic_account_id.action_view_mrp_bom()

    def action_view_workorder(self):
        self.ensure_one()
        return self.analytic_account_id.action_view_workorder()

# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    analytic_plan_id = fields.Many2one(
        'account.analytic.plan',
        string="Default Plan",
        check_company=True,
        readonly=False,
        compute="_compute_analytic_plan_id",
        help="Default Plan for a new analytic account for projects")

    def _compute_analytic_plan_id(self):
        for company in self:
            company.analytic_plan_id = self.env['account.analytic.plan'].with_company(company)._get_default()

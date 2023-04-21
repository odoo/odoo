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
            default_plan = self.env['ir.config_parameter'].with_company(company).sudo().get_param("default_analytic_plan_id_%s" % company.id)
            company.analytic_plan_id = int(default_plan) if default_plan else False
            if not company.analytic_plan_id:
                company.analytic_plan_id = self.env['account.analytic.plan'].with_company(company)._get_default()

    def write(self, values):
        for company in self:
            if 'analytic_plan_id' in values:
                self.env['ir.config_parameter'].sudo().set_param("default_analytic_plan_id_%s" % company.id, values['analytic_plan_id'])
        return super().write(values)

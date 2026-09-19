from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    partner_name = fields.Char(
        related="partner_id.name",
        string="Customer Name",
        readonly=False,
        tracking=False,
    )
    partner_company_name = fields.Char(
        string="Company Name",
        compute="_compute_partner_company_name",
        store=True,
        readonly=False,
        tracking=False,
    )

    @api.depends("partner_id.commercial_company_name")
    def _compute_partner_company_name(self):
        for task in self:
            if company_name := task.partner_id.commercial_company_name:
                task.partner_company_name = company_name
            elif not task.partner_company_name:
                task.partner_company_name = False

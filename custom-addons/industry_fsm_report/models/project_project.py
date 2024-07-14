# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    allow_worksheets = fields.Boolean(
        "Worksheets", compute="_compute_allow_worksheets", store=True, readonly=False)
    worksheet_template_id = fields.Many2one(
        'worksheet.template', compute="_compute_worksheet_template_id", store=True, readonly=False,
        string="Default Worksheet",
        domain="[('res_model', '=', 'project.task'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]")

    @api.depends('is_fsm')
    def _compute_allow_worksheets(self):
        for project in self:
            project.allow_worksheets = project.is_fsm

    @api.depends('allow_worksheets')
    def _compute_worksheet_template_id(self):
        default_worksheet = self.env.ref('industry_fsm_report.fsm_worksheet_template', False)
        project_ids = []
        for project in self:
            if not project.worksheet_template_id:
                if project.allow_worksheets:
                    if default_worksheet and (not project.company_id or not default_worksheet.company_ids or project.company_id in default_worksheet.company_ids):
                        project.worksheet_template_id = default_worksheet
                    else:
                        project_ids.append(project.id)
                else:
                    project.worksheet_template_id = False
        if project_ids:
            projects = self.browse(project_ids)
            if len(projects.company_id) == 1:
                projects.worksheet_template_id = self.env['worksheet.template'].search([('company_ids', 'in', [projects.company_id.id, False])], limit=1)
            else:
                worksheet_per_company = {
                    company: worksheets[:1]
                    for company, worksheets in self.env['worksheet.template']._read_group(
                        [('company_ids', 'in', [*projects.company_id.ids, False])],
                        ['company_ids'],
                        ['id:recordset'],
                    )
                }
                for project in projects:
                    project.worksheet_template_id = worksheet_per_company.get(project.company_id, False)

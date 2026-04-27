# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    allow_worksheets = fields.Boolean(
        "Worksheets", compute="_compute_allow_worksheets", store=True, readonly=False)
    worksheet_template_id = fields.Many2one(
        'worksheet.template', compute="_compute_worksheet_template_id", store=True, readonly=False,
        string="Worksheet Template",
        domain="[('res_model', '=', 'project.task'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('is_fsm')
    def _compute_allow_worksheets(self):
        for project in self:
            project.allow_worksheets = project.is_fsm

    @api.depends('allow_worksheets', 'company_id')
    def _compute_worksheet_template_id(self):
        default_worksheet = self.env.ref('industry_fsm_report.fsm_worksheet_template', False)
        project_ids = []
        for project in self:
            if not project.worksheet_template_id:
                if project.allow_worksheets:
                    if default_worksheet and (not project.company_id or not default_worksheet.company_id or project.company_id in default_worksheet.company_id):
                        project.worksheet_template_id = default_worksheet
                    else:
                        project_ids.append(project.id)
                else:
                    project.worksheet_template_id = False
            elif (project.allow_worksheets and project.company_id != project.worksheet_template_id.company_id):
                project_ids.append(project.id)
        if project_ids:
            projects = self.browse(project_ids)
            WorksheetTemplate = self.env['worksheet.template']

            if len(projects.company_id) == 1:
                projects.worksheet_template_id = WorksheetTemplate.search(
                    [('company_id', 'in', [projects.company_id.id, False]), ('res_model', '=', 'project.task')],
                    limit=1,
                    order="company_id, sequence, id DESC",
                )
            else:
                company_worksheets = WorksheetTemplate._read_group(
                    [('company_id', 'in', [*projects.company_id.ids, False]), ('res_model', '=', 'project.task')],
                    ['company_id'],
                    ['id:recordset'],
                )
                worksheet_mapping = {company.id: templates.sorted(key=lambda t: (t.sequence, -t.id))[:1] for company, templates in company_worksheets}

                # Assign the appropriate worksheet template to each project
                for project in projects:
                    project.worksheet_template_id = worksheet_mapping.get(
                        project.company_id.id,
                        worksheet_mapping.get(False, False)  # Fallback to a template without a company
                    )

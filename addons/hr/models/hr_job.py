# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.html_editor.tools import handle_history_divergence


class HrJob(models.Model):
    _name = 'hr.job'
    _description = "Job Position"
    _inherit = ['mail.thread']
    _order = 'sequence'

    active = fields.Boolean(default=True)
    name = fields.Char(string='Job Position', required=True, index='trigram', translate=True)
    sequence = fields.Integer(default=10)
    expected_employees = fields.Integer(compute='_compute_employees', string='Total Forecasted Employees',
        help='Expected number of employees for this job position after new recruitment.', groups="hr.group_hr_user")
    no_of_employee = fields.Integer(compute='_compute_employees', string="Current Number of Employees",
        help='Number of employees currently occupying this job position.', groups="hr.group_hr_user")
    no_of_recruitment = fields.Integer(string='Target', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    employee_ids = fields.One2many('hr.employee', 'job_id', string='Employees', groups='base.group_user')
    description = fields.Html(string='Job Description', sanitize_attributes=False)
    requirements = fields.Text('Requirements', groups="hr.group_hr_user")
    user_id = fields.Many2one(
        "res.users",
        "Recruiter",
        domain="[('share', '=', False), ('company_ids', '=?', company_id)]",
        default=lambda self: self.env.user,
        groups="hr.group_hr_user",
        tracking=True,
        help="The Recruiter will be the default value for all Applicants in this job \
            position. The Recruiter is automatically added to all meetings with the Applicant.",
    )
    # TODO (master): remove the field `allowed_user_ids`.
    allowed_user_ids = fields.Many2many('res.users', compute='_compute_allowed_user_ids', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', check_company=True, tracking=True, index='btree_not_null')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    contract_type_id = fields.Many2one('hr.contract.type', string='Employment Type', tracking=True)

    _name_company_uniq = models.Constraint(
        'unique(name, company_id, department_id)',
        'The name of the job position must be unique per department in company!',
    )
    _no_of_recruitment_positive = models.Constraint(
        'CHECK(no_of_recruitment >= 0)',
        'The expected number of new employees must be positive.',
    )

    @api.depends('no_of_recruitment', 'employee_ids.job_id', 'employee_ids.active')
    def _compute_employees(self):
        employee_data = self.env['hr.employee']._read_group([('job_id', 'in', self.ids)], ['job_id'], ['__count'])
        result = {job.id: count for job, count in employee_data}
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

    @api.depends("company_id")
    def _compute_allowed_user_ids(self):
        company_ids = self.mapped("company_id.id")
        domain = [("share", "=", False)]
        if company_ids:
            domain += [("company_ids", "in", company_ids)]

        users_by_company = dict(
            self.env["res.users"]._read_group(
                domain=domain,
                groupby=["company_id"],
                aggregates=["id:recordset"],
            ),
        )

        all_users = self.env["res.users"]
        for users in users_by_company.values():
            all_users |= users

        for job in self:
            job.allowed_user_ids = users_by_company.get(job.company_id, all_users)

    @api.model_create_multi
    def create(self, vals_list):
        """ We don't want the current user to be follower of all created job """
        return super(HrJob, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", job.name)) for job, vals in zip(self, vals_list)]

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        return super().write(vals)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.html_editor.tools import handle_history_divergence


class HrJob(models.Model):
    _name = 'hr.job'
    _description = "Job Position"
    _inherit = ['mail.thread']
    _order = 'sequence'

    def _recruiter_domain(self):
        return [
            ("user_id", "!=", False),
            ("user_id.share", "=", False),
        ]

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
    recruiter_id = fields.Many2one(
        'hr.employee',
        "Recruiter",
        domain=_recruiter_domain,
        check_company=True,
        default=lambda self: self.env.user.employee_id,
        groups="hr.group_hr_user",
        tracking=True,
        help="The Recruiter will be the default value for all Applicants in this job \
            position. The Recruiter is automatically added to all meetings with the Applicant.",
    )
    department_id = fields.Many2one('hr.department', string='Department', check_company=True, tracking=True, index='btree_not_null')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    contract_type_id = fields.Many2one('hr.contract.type', string='Contract Type', tracking=True)

    job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        inverse_name="job_id",
        string="Skills",
        domain=[("skill_type_id.active", "=", True)],
    )
    current_job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        compute="_compute_current_job_skill_ids",
        search="_search_current_job_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        compute="_compute_skill_ids",
        store=True,
    )

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

    @api.depends("job_skill_ids")
    def _compute_current_job_skill_ids(self):
        for job in self:
            job.current_job_skill_ids = job.job_skill_ids.filtered(
                lambda skill: not skill.valid_to or skill.valid_to >= fields.Date.today()
            )

    def _search_current_job_skill_ids(self, operator, value):
        if operator not in ('in', 'not in', 'any'):
            raise NotImplementedError()
        job_skill_ids = []
        domain = Domain.OR([
            Domain('valid_to', '=', False),
            Domain('valid_to', '>=', fields.Date.today()),
        ])
        if operator == 'any' and isinstance(value, Domain):
            domain = Domain.AND([domain, value])

        elif operator in ('in', 'not in'):
            domain = Domain.AND([domain, Domain('id', 'in', value)])

        job_skill_ids = self.env['hr.job.skill']._search(domain)
        return Domain('job_skill_ids', 'in', job_skill_ids)

    @api.depends("job_skill_ids.skill_id")
    def _compute_skill_ids(self):
        for job in self:
            job.skill_ids = job.job_skill_ids.skill_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals_job_skill = vals.pop("current_job_skill_ids", []) + vals.get("job_skill_ids", [])
            vals["job_skill_ids"] = self.env["hr.job.skill"]._get_transformed_commands(vals_job_skill, self)
        # We don't want the current user to be follower of all created job
        return super(HrJob, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", job.name)) for job, vals in zip(self, vals_list)]

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        if "current_job_skill_ids" in vals or "job_skill_ids" in vals:
            vals_job_skill = vals.pop("current_job_skill_ids", []) + vals.get("job_skill_ids", [])
            vals["job_skill_ids"] = self.env["hr.job.skill"]._get_transformed_commands(vals_job_skill, self)
        return super().write(vals)

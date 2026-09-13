from odoo import api, fields, models

from ..tools import debug_log as dbg
from odoo.addons.base.models.mixin_catalog import name_uniq_index
from odoo.addons.html_editor.tools import handle_history_divergence


class HrJob(models.Model):
    _name = "hr.job"
    _description = "Job Position"
    _inherit = ["mixin.mail.thread"]
    _order = "sequence"

    active = fields.Boolean(default=True)
    name = fields.Char(
        string="Job Position",
        translate=True,
        index="trigram",
        required=True,
    )
    sequence = fields.Integer(default=10)
    expected_employees = fields.Integer(
        string="Total Forecasted Employees",
        compute="_compute_employee_counts",
        groups="hr.group_hr_user",
        help="Expected number of employees for this job position after new recruitment.",
    )
    no_of_employee = fields.Integer(
        string="Current Number of Employees",
        compute="_compute_employee_counts",
        groups="hr.group_hr_user",
        help="Number of employees currently occupying this job position.",
    )
    no_of_recruitment = fields.Integer(
        string="Target",
        default=1,
        copy=False,
        help="Number of new employees you expect to recruit.",
    )
    employee_ids = fields.One2many(
        comodel_name="hr.employee",
        inverse_name="job_id",
        string="Employees",
        groups="base.group_user",
    )
    description = fields.Html(
        string="Job Description",
        sanitize_attributes=False,
    )
    requirements = fields.Text(groups="hr.group_hr_user")
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Recruiter",
        default=lambda self: self.env.user,
        domain="[('share', '=', False), ('company_ids', '=?', company_id)]",
        tracking=True,
        groups="hr.group_hr_user",
        help="The Recruiter will be the default value for all Applicants in this job \
            position. The Recruiter is automatically added to all meetings with the Applicant.",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        index="btree_not_null",
        check_company=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        tracking=True,
    )
    contract_type_id = fields.Many2one(
        comodel_name="hr.contract.type",
        string="Employment Type",
        tracking=True,
    )

    _name_src_uniq = name_uniq_index(
        "company_id",
        "department_id",
        nulls_distinct=True,
        message="The name of the job position must be unique per department in company!",
    )
    _name_src_uniq_no_department = name_uniq_index(
        "company_id",
        nulls_distinct=True,
        where="department_id IS NULL",
        message="The name of the job position must be unique per department in company!",
    )
    _no_of_recruitment_positive = models.Constraint(
        "CHECK(no_of_recruitment >= 0)",
        "The expected number of new employees must be positive.",
    )

    @dbg.timed
    @api.depends("no_of_recruitment", "employee_ids.job_id", "employee_ids.active")
    def _compute_employee_counts(self):
        employee_data = self.env["hr.employee"]._read_group(
            [("job_id", "in", self.ids)], ["job_id"], ["__count"]
        )
        result = {job.id: count for job, count in employee_data}
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "hr.job.create: %d vals, keys=%s", len(vals_list), dbg.vals_keys(vals_list)
        )
        jobs = super(HrJob, self.with_context(mail_create_nosubscribe=True)).create(
            vals_list
        )
        dbg.lifecycle.debug("hr.job.create: created %s", dbg.rec(jobs))
        return jobs

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", job.name))
            for job, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "hr.job.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if len(self) == 1:
            handle_history_divergence(self, "description", vals)
        return super().write(vals)

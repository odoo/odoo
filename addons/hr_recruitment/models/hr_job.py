from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.convert import convert_file

_debug = DebugLog(__name__)


class HrJob(models.Model):
    _name = "hr.job"
    _inherit = [
        "mixin.mail.alias",
        "hr.job",
        "mixin.mail.activity",
        "mixin.user.favorite",
    ]
    _order = "sequence, name asc"

    @api.model
    def _default_address_id(self):
        last_used_address = self.env["hr.job"].search(
            [("company_id", "in", self.env.companies.ids)], order="id desc", limit=1
        )
        if last_used_address:
            return last_used_address.address_id
        else:
            return self.env.company.partner_id

    def _domain_address_id(self):
        return [
            "|",
            "&",
            "&",
            ("type", "!=", "contact"),
            ("type", "!=", "private"),
            ("id", "in", self.sudo().env.companies.partner_id.child_ids.ids),
            ("id", "in", self.sudo().env.companies.partner_id.ids),
        ]

    def _default_favorite_user_ids(self):
        return [Command.set([self.env.uid])]

    expected_employees = fields.Integer(
        groups="hr_recruitment.group_hr_recruitment_interviewer,hr.group_hr_user"
    )
    no_of_employee = fields.Integer(
        groups="hr_recruitment.group_hr_recruitment_interviewer,hr.group_hr_user"
    )
    requirements = fields.Text(
        groups="hr_recruitment.group_hr_recruitment_interviewer,hr.group_hr_user"
    )
    user_id = fields.Many2one(
        groups="hr_recruitment.group_hr_recruitment_interviewer,hr.group_hr_user"
    )

    address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Job Location",
        default=_default_address_id,
        domain=lambda self: self._domain_address_id(),
        tracking=True,
        help="Select the location where the applicant will work. Addresses listed here are defined on the company's contact information.",
    )
    application_ids = fields.One2many(
        comodel_name="hr.applicant",
        inverse_name="job_id",
        string="Job Applications",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    application_count = fields.Integer(
        compute="_compute_application_counts",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    open_application_count = fields.Integer(
        compute="_compute_open_application_count",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
        help="Number of applications that are still ongoing (not hired or refused)",
    )
    all_application_count = fields.Integer(
        compute="_compute_all_application_count",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    new_application_count = fields.Integer(
        string="New Application",
        compute="_compute_application_counts",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
        help="Number of applications that are new in the flow (typically at first step of the flow)",
    )
    old_application_count = fields.Integer(
        string="Old Application",
        compute="_compute_old_application_count",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    applicant_hired = fields.Integer(
        string="Applicants Hired",
        compute="_compute_application_counts",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        related="department_id.manager_id",
        string="Department Manager",
        readonly=True,
        groups="hr_recruitment.group_hr_recruitment_interviewer,hr.group_hr_user",
    )
    document_ids = fields.One2many(
        comodel_name="ir.attachment",
        string="Documents",
        compute="_compute_documents",
        readonly=True,
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    documents_count = fields.Count(
        count_of="document_ids",
        string="Document Count",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    employee_count = fields.Integer(compute="_compute_employee_count")
    alias_id = fields.Many2one(
        groups="hr_recruitment.group_hr_recruitment_interviewer",
        help="Email alias for this job position. New emails will automatically create new applicants for this job position.",
    )
    color = fields.Integer(string="Color Index")
    favorite_user_ids = fields.Many2many(
        relation="job_favorite_user_rel",
        column1="job_id",
        column2="user_id",
        default=_default_favorite_user_ids,
    )
    interviewer_ids = fields.Many2many(
        comodel_name="res.users",
        string="Interviewers",
        domain="[('share', '=', False), ('company_ids', '=?', company_id)]",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
        help="The Interviewers set on the job position can see all Applicants in it. They have access to the information, the attachments, the meeting management and they can refuse him. You don't need to have Recruitment rights to be set as an interviewer.",
    )
    extended_interviewer_ids = fields.Many2many(
        comodel_name="res.users",
        relation="hr_job_extended_interviewer_res_users",
        compute="_compute_extended_interviewer_ids",
        store=True,
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    industry_id = fields.Many2one(
        comodel_name="res.partner.industry",
        tracking=True,
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    expected_degree = fields.Many2one(
        comodel_name="hr.recruitment.degree",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    activity_count = fields.Integer(
        compute="_compute_activity_count",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    job_properties = fields.Properties(
        definition="company_id.job_properties_definition",
        string="Properties",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    applicant_properties_definition = fields.PropertiesDefinition(
        string="Applicant Properties",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )
    no_of_hired_employee = fields.Integer(
        string="Hired",
        compute="_compute_no_of_hired_employee",
        store=True,
        copy=False,
        groups="hr_recruitment.group_hr_recruitment_interviewer",
        help="Number of hired employees for this job position during recruitment phase.",
    )

    job_source_ids = fields.One2many(
        comodel_name="hr.recruitment.source",
        inverse_name="job_id",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    @api.depends("application_ids.date_closed")
    def _compute_no_of_hired_employee(self):
        counts = dict(
            self.env["hr.applicant"]
            .with_context(active_test=False)
            ._read_group(
                domain=[("job_id", "in", self.ids), ("date_closed", "!=", False)],
                groupby=["job_id"],
                aggregates=["__count"],
            )
        )
        for job in self:
            job.no_of_hired_employee = counts.get(job, 0)

    @api.depends_context("uid")
    def _compute_activity_count(self):
        """This user's activities on the still-running applications of these jobs.

        The applications used to be *loaded* only to build an id -> job map, so a
        job with ten thousand applications read ten thousand records to count a
        handful of activities. The set is narrowed in SQL instead, and only the
        applications that actually carry one of this user's activities are
        mapped back to their job.
        """
        running = self.env["hr.applicant"]._search(
            [("job_id", "in", self.ids), ("stage_id.hired_stage", "!=", True)]
        )
        counts_by_applicant = dict(
            self.env["mail.activity"]._read_group(
                [
                    ("res_model", "=", "hr.applicant"),
                    ("res_id", "in", running.subselect()),
                    ("user_id", "=", self.env.uid),
                ],
                ["res_id"],
                ["__count"],
            )
        )
        activity_count_by_job = defaultdict(int)
        if counts_by_applicant:
            for job, applicants in self.env["hr.applicant"]._read_group(
                [("id", "in", list(counts_by_applicant))],
                ["job_id"],
                ["id:recordset"],
            ):
                for applicant in applicants:
                    activity_count_by_job[job] += counts_by_applicant[applicant.id]
        _debug.perf.count(
            "activity_count",
            jobs=len(self),
            applicants_with_activities=len(counts_by_applicant),
        )
        for job in self:
            job.activity_count = activity_count_by_job[job]

    @api.depends("application_ids.interviewer_ids")
    def _compute_extended_interviewer_ids(self):
        """Every interviewer named on any application of these jobs.

        Aggregated rather than read: ``search_read`` loaded each application and
        rendered ``job_id``'s display name only to throw both away.
        """
        interviewers_by_job = defaultdict(set)
        for job, interviewer in (
            self.env["hr.applicant"]
            .sudo()
            ._read_group(
                [("job_id", "in", self.ids), ("interviewer_ids", "!=", False)],
                ["job_id", "interviewer_ids"],
            )
        ):
            interviewers_by_job[job.id].add(interviewer.id)
        for job in self:
            job.extended_interviewer_ids = [
                Command.set(list(interviewers_by_job[job.id]))
            ]

    def _compute_documents(self):
        """Documents on these jobs and on their applications that became nobody.

        The application ids are collected by aggregate rather than by loading
        `application_ids` for every job, which fetched whole applicant rows to
        read one column off each.
        """
        job_by_applicant_id = {
            applicant.id: job
            for job, applicants in self.env["hr.applicant"]._read_group(
                [("job_id", "in", self.ids), ("employee_id", "=", False)],
                ["job_id"],
                ["id:recordset"],
            )
            for applicant in applicants
        }
        attachments = self.env["ir.attachment"].search(
            [
                "|",
                "&",
                ("res_model", "=", "hr.job"),
                ("res_id", "in", self.ids),
                "&",
                ("res_model", "=", "hr.applicant"),
                ("res_id", "in", list(job_by_applicant_id)),
            ]
        )
        result = dict.fromkeys(self, self.env["ir.attachment"])
        for attachment in attachments:
            if attachment.res_model == "hr.applicant":
                job = job_by_applicant_id[attachment.res_id]
            else:
                job = self.browse(attachment.res_id)
            result[job] |= attachment

        for job in self:
            job.document_ids = result[job]

    def _compute_all_application_count(self):
        read_group_result = (
            self.env["hr.applicant"]
            .with_context(active_test=False)
            ._read_group(
                [
                    ("job_id", "in", self.ids),
                    "|",
                    ("active", "=", True),
                    "&",
                    ("active", "=", False),
                    ("refuse_reason_id", "!=", False),
                ],
                ["job_id"],
                ["__count"],
            )
        )
        result = {job.id: count for job, count in read_group_result}
        for job in self:
            job.all_application_count = result.get(job.id, 0)

    def _compute_application_counts(self):
        """Total, hired and first-stage application counts in one read_group.

        The three used to be three ``_read_group`` calls over the same active
        applications, so a job kanban paid for the same scan three times.
        """
        first_stage_by_job = self.env["hr.recruitment.stage"]._get_first_stage_by_job(
            self
        )
        totals = defaultdict(int)
        hired = defaultdict(int)
        new_in_flow = defaultdict(int)
        with _debug.perf("application_counts", cr=self.env.cr, jobs=len(self)):
            for job, stage, count in self.env["hr.applicant"]._read_group(
                [("job_id", "in", self.ids)], ["job_id", "stage_id"], ["__count"]
            ):
                totals[job] += count
                if stage.hired_stage:
                    hired[job] += count
                if stage == first_stage_by_job.get(job):
                    new_in_flow[job] += count
        for job in self:
            job.application_count = totals[job]
            job.applicant_hired = hired[job]
            job.new_application_count = new_in_flow[job]

    @api.depends("application_count", "applicant_hired")
    def _compute_open_application_count(self):
        for job in self:
            job.open_application_count = job.application_count - job.applicant_hired

    def _compute_employee_count(self):
        res = {
            job.id: count
            for job, count in self.env["hr.employee"]
            .sudo()
            ._read_group(
                domain=[
                    ("job_id", "in", self.ids),
                    ("company_id", "in", self.env.companies.ids),
                ],
                groupby=["job_id"],
                aggregates=["__count"],
            )
        }
        for job in self:
            job.employee_count = res.get(job.id, 0)

    def _get_first_stage(self):
        self.check_singleton()
        return self.env["hr.recruitment.stage"]._get_first_stage_by_job(self)[self]

    @api.depends("application_count", "new_application_count")
    def _compute_old_application_count(self):
        for job in self:
            job.old_application_count = (
                job.application_count - job.new_application_count
            )

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get("hr.applicant").id
        if self.id:
            values["alias_defaults"] = defaults = self._prepare_alias_defaults()
            defaults.update(
                {
                    "job_id": self.id,
                    "department_id": self.department_id.id,
                    "company_id": self.department_id.company_id.id
                    or self.company_id.id,
                    "user_id": self.user_id.id,
                }
            )
        return values

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        _debug.lifecycle("create", jobs=jobs, count=len(vals_list))
        jobs.sudo().interviewer_ids._create_recruitment_interviewers()
        return jobs

    def write(self, vals):
        old_interviewers = (
            self.interviewer_ids if "interviewer_ids" in vals else self.browse()
        )
        old_recruiters = {job: job.user_id for job in self} if "user_id" in vals else {}
        _debug.lifecycle("write", jobs=self, fields=list(vals))
        if "active" in vals:
            if vals["active"]:
                self._unarchive_cascaded_applications()
            else:
                self._archive_applications()
        res = super().write(vals)
        if "interviewer_ids" in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            _debug.lifecycle(
                "job_interviewers_changed",
                jobs=self,
                removed=interviewers_to_clean,
                kept=self.interviewer_ids,
            )
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()

        if "user_id" in vals:
            for job in self:
                to_unsubscribe = [
                    partner
                    for partner in old_recruiters[job].partner_id.ids
                    if partner not in job.manager_id._get_related_partners().ids
                ]
                job.message_unsubscribe(to_unsubscribe)
                application_ids = job.application_ids.filtered(
                    lambda x, job=job: (
                        x.user_id == old_recruiters[job]
                        and x.application_status == "ongoing"
                    )
                )
                if application_ids:
                    _debug.pipeline(
                        "recruiter_changed",
                        job=job,
                        was=old_recruiters[job],
                        now=job.user_id,
                        applications=application_ids,
                    )
                    application_ids.message_unsubscribe(to_unsubscribe)
                    application_ids.with_context(
                        mail_auto_subscribe_no_notify=True
                    ).user_id = job.user_id

        if "department_id" in vals or "user_id" in vals:
            _debug.pipeline("alias_defaults_refreshed", jobs=self)
            for job in self:
                job.alias_defaults = job._alias_get_creation_values()["alias_defaults"]
        return res

    def _archive_applications(self):
        """Archive the applications still running on these jobs, reversibly.

        Only the active ones: an application refused on its own is already
        archived and must not be restored by restoring the job.
        """
        applications = self.application_ids
        _debug.lifecycle("cascade_archive", jobs=self, applications=len(applications))
        if applications:
            applications.write({"active": False, "archived_with_job": True})

    def _unarchive_cascaded_applications(self):
        applications = self.with_context(active_test=False).application_ids.filtered(
            "archived_with_job"
        )
        _debug.lifecycle("cascade_unarchive", jobs=self, applications=len(applications))
        if applications:
            applications.write({"active": True, "archived_with_job": False})

    def _creation_subtype(self):
        return self.env.ref("hr_recruitment.mt_job_new")

    def action_view_attachments(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "name": _("Documents"),
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.ids[0],
                "show_partner_name": 1,
            },
            "view_mode": "list",
            "views": [
                (
                    self.env.ref(
                        "hr_recruitment.ir_attachment_hr_recruitment_list_view"
                    ).id,
                    "list",
                )
            ],
            "search_view_id": self.env.ref(
                "hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment"
            ).ids,
            "domain": [
                "|",
                "&",
                ("res_model", "=", "hr.job"),
                ("res_id", "in", self.ids),
                "&",
                ("res_model", "=", "hr.applicant"),
                ("res_id", "in", self.application_ids.ids),
            ],
        }

    def action_view_activities(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_recruitment.action_hr_job_applications"
        )
        views = ["activity"] + [
            view for view in action["view_mode"].split(",") if view != "activity"
        ]
        action["view_mode"] = ",".join(views)
        action["views"] = [(False, view) for view in views]
        action["context"] = {
            "default_job_id": self.id,
            "search_default_job_id": self.id,
            "search_default_running_applicant_activities": True,
        }
        return action

    @api.model
    def is_recruitment_scenario_loaded(self):
        """Whether ``_action_load_recruitment_scenario`` has already run.

        Keyed on the scenario's xml id rather than on a tag label, so a tag a
        user happens to name "Demo" neither hides nor fakes the scenario.
        """
        return bool(
            self.env.ref("hr_recruitment.tag_applicant_demo", raise_if_not_found=False)
        )

    @api.model
    def _action_load_recruitment_scenario(self):
        convert_file(
            self.sudo().env,
            "hr_recruitment",
            "data/scenarios/hr_recruitment_scenario.xml",
            None,
            mode="init",
        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_view_employees(self):
        self.check_singleton()
        return {
            "name": _("Related Employees"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "list,kanban,form",
            "views": [(False, "list"), (False, "kanban"), (False, "form")],
            "domain": [("company_id", "in", self.env.companies.ids)],
            "context": {
                "default_job_id": self.id,
                "search_default_group_job": 1,
                "search_default_job_id": self.id,
                "expand": 1,
            },
        }

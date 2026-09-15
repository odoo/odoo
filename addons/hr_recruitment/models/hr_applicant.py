import re
from collections import defaultdict

from markupsafe import Markup

from odoo import Command, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import clean_context
from odoo.tools.translate import _

_debug = DebugLog(__name__)

AVAILABLE_PRIORITIES = [
    ("0", "Normal"),
    ("1", "Good"),
    ("2", "Very Good"),
    ("3", "Excellent"),
]


class HrApplicant(models.Model):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "sequence"
    _inherit = [
        "mixin.mail.thread.cc",
        "mixin.mail.thread.main.attachment",
        "mixin.mail.thread.blacklist",
        "mixin.mail.thread.phone",
        "mixin.mail.activity",
        "mixin.utm",
        "mixin.mail.tracking.duration",
    ]
    _rec_name = "partner_name"
    _mailing_enabled = True
    _primary_email = "email_from"
    _track_duration_field = "stage_id"

    sequence = fields.Integer(
        default=10,
        index=True,
    )
    active = fields.Boolean(
        default=True,
        index=True,
        help="If the active field is set to false, it will allow you to hide the case without removing it.",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index="btree_not_null",
        copy=False,
    )
    partner_name = fields.Char(string="Applicant's Name")
    email_from = fields.Char(
        string="Email",
        size=128,
        compute="_compute_partner_phone_email",
        inverse="_inverse_partner_email",
        store=True,
        index="trigram",
        copy=True,
    )
    email_normalized = fields.Char(index="trigram")
    phone_sanitized = fields.Char(index="btree_not_null")
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="hr_applicant_phone_number_rel",
        column1="applicant_id",
        column2="phone_number_id",
        compute="_compute_partner_phone_email",
        inverse="_inverse_partner_email",
        store=True,
        copy=True,
    )
    linkedin_profile = fields.Char(
        string="LinkedIn Profile",
        index="btree_not_null",
    )
    degree_id = fields.Many2one(comodel_name="hr.recruitment.degree")
    availability = fields.Date(
        tracking=True,
        help="The date at which the applicant will be available to start working",
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index="btree_not_null",
        copy=False,
        help="Employee linked to the applicant.",
    )
    emp_is_active = fields.Boolean(
        related="employee_id.active",
        string="Employee Active",
    )
    employee_name = fields.Char(
        related="employee_id.name",
        string="Employee Name",
    )

    create_date = fields.Datetime(
        string="Applied on",
        readonly=True,
    )
    stage_id = fields.Many2one(
        comodel_name="hr.recruitment.stage",
        compute="_compute_stage_id",
        store=True,
        index=True,
        copy=False,
        readonly=False,
        group_expand="_read_group_stage_ids",
        domain="['|', ('job_ids', '=', False), ('job_ids', '=', job_id)]",
        ondelete="restrict",
        tracking=True,
    )
    last_stage_id = fields.Many2one(
        comodel_name="hr.recruitment.stage",
        help="Stage of the applicant before being in the current stage. Used for lost cases analysis.",
    )
    categ_ids = fields.Many2many(
        comodel_name="hr.applicant.category",
        string="Tags",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
        readonly=False,
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Recruiter",
        compute="_compute_user_id",
        store=True,
        readonly=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
    )
    date_closed = fields.Datetime(
        string="Hire Date",
        compute="_compute_date_closed",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
    )
    date_open = fields.Datetime(
        string="Assigned",
        readonly=True,
    )
    date_last_stage_update = fields.Datetime(
        string="Last Stage Update",
        default=fields.Datetime.now,
        index=True,
    )
    priority = fields.Selection(
        selection=AVAILABLE_PRIORITIES,
        string="Evaluation",
        default="0",
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        string="Job Position",
        index=True,
        copy=False,
        domain="company_id and [('company_id', '=', company_id)] or []",
        tracking=True,
    )
    salary_proposed_extra = fields.Char(
        string="Proposed Salary Extra",
        tracking=True,
        groups="hr_recruitment.group_hr_recruitment_user",
        help="Salary Proposed by the Organisation, extra advantages",
    )
    salary_expected_extra = fields.Char(
        string="Expected Salary Extra",
        tracking=True,
        groups="hr_recruitment.group_hr_recruitment_user",
        help="Salary Expected by Applicant, extra advantages",
    )
    salary_proposed = fields.Float(
        string="Proposed",
        aggregator="avg",
        tracking=True,
        groups="hr_recruitment.group_hr_recruitment_user",
        help="Salary Proposed by the Organisation",
    )
    salary_expected = fields.Float(
        string="Expected",
        aggregator="avg",
        tracking=True,
        groups="hr_recruitment.group_hr_recruitment_user",
        help="Salary Expected by Applicant",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    delay_close = fields.Float(
        string="Delay to Close",
        compute="_compute_delay_close",
        store=True,
        readonly=True,
        aggregator="avg",
        help="Number of days to close",
    )
    user_email = fields.Char(
        related="user_id.email",
        string="User Email",
        readonly=True,
    )
    attachment_number = fields.Integer(
        string="Number of Attachments",
        compute="_compute_attachment_number",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
        domain=[("res_model", "=", "hr.applicant")],
    )
    kanban_state = fields.Selection(
        selection=[
            ("normal", "In Progress"),
            ("done", "Ready for Next Stage"),
            ("waiting", "Waiting"),
            ("blocked", "Blocked"),
        ],
        default="normal",
        copy=False,
        required=True,
    )
    legend_blocked = fields.Char(
        related="stage_id.legend_blocked",
        string="Kanban Blocked",
    )
    legend_done = fields.Char(
        related="stage_id.legend_done",
        string="Kanban Valid",
    )
    legend_waiting = fields.Char(
        related="stage_id.legend_waiting",
        string="Kanban Waiting",
    )
    legend_normal = fields.Char(
        related="stage_id.legend_normal",
        string="Kanban Ongoing",
    )
    refuse_reason_id = fields.Many2one(
        comodel_name="hr.applicant.refuse.reason",
        tracking=True,
    )
    meeting_ids = fields.One2many(
        comodel_name="calendar.event",
        inverse_name="applicant_id",
        string="Meetings",
    )
    meeting_display_text = fields.Char(compute="_compute_meeting_display")
    meeting_display_date = fields.Date(compute="_compute_meeting_display")
    campaign_id = fields.Many2one(ondelete="set null")
    medium_id = fields.Many2one(
        ondelete="set null",
        help="This displays how the applicant has reached out, e.g. via Email, LinkedIn, Website, etc.",
    )
    source_id = fields.Many2one(ondelete="set null")
    interviewer_ids = fields.Many2many(
        comodel_name="res.users",
        relation="hr_applicant_res_users_interviewers_rel",
        string="Interviewers",
        copy=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True,
    )
    application_status = fields.Selection(
        selection=[
            ("ongoing", "Ongoing"),
            ("hired", "Hired"),
            ("refused", "Refused"),
            ("archived", "Archived"),
        ],
        compute="_compute_application_status",
        search="_search_application_status",
    )
    application_count = fields.Integer(
        compute="_compute_application_count",
        help="Applications with the same email or phone or mobile",
    )
    applicant_properties = fields.Properties(
        definition="job_id.applicant_properties_definition",
        string="Properties",
        copy=True,
    )
    applicant_notes = fields.Html()
    refuse_date = fields.Datetime()
    archived_with_job = fields.Boolean(
        copy=False,
        help="Archived because its job position was archived, rather than on its "
        "own. Restoring the job position restores these.",
    )
    talent_pool_ids = fields.Many2many(
        comodel_name="hr.talent.pool",
        string="Talent Pools",
    )
    pool_applicant_id = fields.Many2one(
        comodel_name="hr.applicant",
        index="btree_not_null",
    )
    is_pool_applicant = fields.Boolean(compute="_compute_is_pool_applicant")
    is_applicant_in_pool = fields.Boolean(
        compute="_compute_talent_pool",
        search="_search_is_applicant_in_pool",
    )
    talent_pool_count = fields.Integer(compute="_compute_talent_pool")

    _DUPLICATE_KEY_FIELDS = (
        "email_normalized",
        "phone_sanitized",
        "linkedin_profile",
    )

    _email_normalized_idx = models.Index(
        "(email_normalized) WHERE email_normalized IS NOT NULL"
    )
    _job_id_stage_id_idx = models.Index("(job_id, stage_id) WHERE active IS TRUE")

    @api.constrains("talent_pool_ids", "pool_applicant_id")
    def _check_talent_pool_required(self):
        for talent in self:
            if talent.pool_applicant_id == talent and not talent.talent_pool_ids:
                raise ValidationError(
                    self.env._("Talent must belong to at least one Talent Pool.")
                )

    def _get_domain_duplicate_key(self):
        domains = []
        for fname in self._DUPLICATE_KEY_FIELDS:
            values = [value for value in self.mapped(fname) if value]
            if values:
                domains.append(Domain(fname, "in", values))
        return Domain.OR(domains) if domains else Domain.FALSE

    @api.depends(
        "talent_pool_ids",
        "pool_applicant_id.talent_pool_ids",
        "email_normalized",
        "phone_sanitized",
        "linkedin_profile",
    )
    def _compute_talent_pool(self):
        direct = self.filtered(lambda a: a.talent_pool_ids or a.pool_applicant_id)
        _debug.logic("talent_pool_split", direct=direct, indirect=self - direct)
        for applicant in direct:
            applicant.is_applicant_in_pool = True
            # A talent being created is its own pool holder before ``create`` has
            # linked ``pool_applicant_id``, so fall back to its own pools.
            pools = (
                applicant.pool_applicant_id.talent_pool_ids or applicant.talent_pool_ids
            )
            applicant.talent_pool_count = len(pools)
        indirect = self - direct
        if not indirect:
            return

        key_domain = indirect._get_domain_duplicate_key()
        pool_ids_by_key = {}
        if not key_domain.is_false():
            in_pool = self.env["hr.applicant"].search(
                Domain.OR(
                    [
                        Domain("talent_pool_ids", "!=", False),
                        Domain("pool_applicant_id", "!=", False),
                    ]
                )
                & key_domain
            )
            for applicant in in_pool:
                pool_ids = applicant.pool_applicant_id.talent_pool_ids.ids
                for fname in self._DUPLICATE_KEY_FIELDS:
                    if applicant[fname]:
                        key = (fname, applicant[fname])
                        pool_ids_by_key[key] = pool_ids_by_key.get(key, set()) | set(
                            pool_ids
                        )
        for applicant in indirect:
            matches = [
                pool_ids_by_key[fname, applicant[fname]]
                for fname in self._DUPLICATE_KEY_FIELDS
                if applicant[fname] and (fname, applicant[fname]) in pool_ids_by_key
            ]
            # The keys can match different talents, hence different pools: the
            # count is the union, not whichever key happened to be checked first.
            pools = set().union(*matches) if matches else ()
            _debug.logic(
                "talent_pool_match",
                applicant=applicant,
                keys_matched=len(matches),
                pools=len(pools),
            )
            applicant.is_applicant_in_pool = bool(matches)
            applicant.talent_pool_count = len(pools)

    @api.depends(lambda self: self._phone_get_sanitize_triggers())
    def _compute_phone_sanitized(self):
        for applicant in self:
            applicant.phone_sanitized = applicant.phone_ids._primary().sanitized

    @api.depends("partner_id")
    def _compute_partner_phone_email(self):
        for applicant in self:
            if not applicant.partner_id:
                continue
            applicant.email_from = applicant.partner_id.email
            if not applicant.phone_ids:
                applicant.phone_ids = applicant.partner_id.phone_ids

    def _inverse_partner_email(self):
        """Push the applicant's contact details onto their contact record.

        Shared by ``email_from`` and ``phone_ids``: only *creating* the contact
        needs an email, so the sync below is gated on having a contact, not on
        having an email -- otherwise a phone set on an email-less applicant is
        silently dropped.
        """
        for applicant in self:
            email_normalized = tools.email_normalize(applicant.email_from or "")
            if email_normalized and not applicant.partner_id:
                if not applicant.partner_name:
                    raise UserError(
                        _("You must define a Contact Name for this applicant.")
                    )
                applicant.partner_id = (
                    applicant._partner_get_or_create_from_emails_single(
                        [applicant.email_from],
                        no_create=False,
                        additional_values={email_normalized: {"lang": self.env.lang}},
                    )
                )
            partner = applicant.partner_id
            if not partner:
                continue
            if email_normalized:
                # Name and e-mail stay on the e-mail path they have always been on:
                # `partner_id` is a plain m2o with no domain, so it can be a contact
                # the recruiter picked, and writing a name onto one is not this
                # defect's business.
                if applicant.partner_name and applicant.partner_name != partner.name:
                    partner.name = applicant.partner_name
                if email_normalized != partner.email:
                    partner.email = applicant.email_from
            if applicant.phone_ids and applicant.phone_ids != partner.phone_ids:
                _debug.logic(
                    "partner_phone_sync",
                    applicant=applicant,
                    partner=partner,
                    phones=len(applicant.phone_ids),
                )
                partner.phone_ids = [Command.set(applicant.phone_ids.ids)]

    @api.depends("email_normalized", "phone_sanitized", "linkedin_profile")
    def _compute_application_count(self):
        domain = self._get_domain_similar_applicants(ignore_talent=True)
        matching_applicants = (
            self.env["hr.applicant"].with_context(active_test=False).search(domain)
        )
        _debug.perf.count(
            "similar_applicants_scanned",
            applicants=self,
            matched=matching_applicants,
        )

        email_map = defaultdict(set)
        phone_map = defaultdict(set)
        linkedin_map = defaultdict(set)
        pool_applicant_map = defaultdict(set)
        for app in matching_applicants:
            if app.email_normalized:
                email_map[app.email_normalized].add(app.id)
            if app.phone_sanitized:
                phone_map[app.phone_sanitized].add(app.id)
            if app.linkedin_profile:
                linkedin_map[app.linkedin_profile].add(app.id)
            if app.pool_applicant_id:
                pool_applicant_map[app.pool_applicant_id].add(app.id)

        for applicant in self:
            related_ids = set()
            if applicant.email_normalized:
                related_ids.update(email_map.get(applicant.email_normalized, set()))
            if applicant.phone_sanitized:
                related_ids.update(phone_map.get(applicant.phone_sanitized, set()))
            if applicant.linkedin_profile:
                related_ids.update(linkedin_map.get(applicant.linkedin_profile, set()))
            if applicant.pool_applicant_id:
                related_ids.update(
                    pool_applicant_map.get(applicant.pool_applicant_id, set())
                )

            applicant.application_count = len(related_ids)

    @api.depends("talent_pool_ids")
    def _compute_is_pool_applicant(self):
        for applicant in self:
            applicant.is_pool_applicant = applicant.talent_pool_ids

    def _get_domain_similar_applicants(self, ignore_talent=False, only_talent=False):
        domain = (
            Domain("id", "in", self.ids)
            | self._get_domain_duplicate_key()
            | Domain("pool_applicant_id", "in", self.pool_applicant_id.ids)
        )
        if ignore_talent:
            domain &= Domain("talent_pool_ids", "=", False)
        if only_talent:
            domain &= Domain("talent_pool_ids", "!=", False)
        return domain

    def _search_is_applicant_in_pool(self, operator, value):
        if operator != "in":
            return NotImplemented

        pool_domain = Domain("talent_pool_ids", "!=", False) | Domain(
            "pool_applicant_id", "!=", False
        )
        Applicant = self.env["hr.applicant"]
        domain = Domain("id", "in", Applicant._search(pool_domain).subselect())
        for fname in self._DUPLICATE_KEY_FIELDS:
            keyed = Applicant._search(pool_domain & Domain(fname, "!=", False))
            domain |= Domain(fname, "in", keyed.subselect(fname))
        return domain

    @api.depends("date_open", "date_closed")
    def _compute_delay_close(self):
        for applicant in self:
            if applicant.date_open and applicant.date_closed:
                applicant.delay_close = (
                    applicant.date_closed - applicant.date_open
                ).total_seconds() / 86400
            else:
                applicant.delay_close = 0.0

    def _get_rotting_depends_fields(self):
        return super()._get_rotting_depends_fields() + [
            "application_status",
            "date_closed",
        ]

    def _get_domain_rotting_records(self):
        return super()._get_domain_rotting_records() & Domain(
            [
                ("application_status", "=", "ongoing"),
                ("date_closed", "=", False),
            ]
        )

    @api.depends_context("lang")
    @api.depends("meeting_ids", "meeting_ids.start")
    def _compute_meeting_display(self):
        applicant_with_meetings = self.filtered("meeting_ids")
        (self - applicant_with_meetings).update(
            {"meeting_display_text": _("No Meeting"), "meeting_display_date": ""}
        )
        today = fields.Date.today()
        for applicant in applicant_with_meetings:
            count = len(applicant.meeting_ids)
            dates = applicant.meeting_ids.mapped("start")
            min_date, max_date = min(dates).date(), max(dates).date()
            if min_date >= today:
                applicant.meeting_display_date = min_date
            else:
                applicant.meeting_display_date = max_date
            if count == 1:
                applicant.meeting_display_text = _("1 Meeting")
            elif applicant.meeting_display_date >= today:
                applicant.meeting_display_text = _("Next Meeting")
            else:
                applicant.meeting_display_text = _("Last Meeting")

    @api.depends("refuse_reason_id", "date_closed", "active")
    def _compute_application_status(self):
        for applicant in self:
            if applicant.refuse_reason_id:
                applicant.application_status = "refused"
            elif not applicant.active:
                applicant.application_status = "archived"
            elif applicant.date_closed:
                applicant.application_status = "hired"
            else:
                applicant.application_status = "ongoing"

    def _search_application_status(self, operator, value):
        if operator != "in":
            return NotImplemented

        refused = Domain("refuse_reason_id", "!=", False)
        archived = ~refused & Domain("active", "=", False)
        hired = (
            ~refused & Domain("active", "=", True) & Domain("date_closed", "!=", False)
        )
        ongoing = (
            ~refused & Domain("active", "=", True) & Domain("date_closed", "=", False)
        )
        by_status = {
            "refused": refused,
            "archived": archived,
            "hired": hired,
            "ongoing": ongoing,
        }
        return Domain.OR(by_status[status] for status in value if status in by_status)

    def _compute_attachment_number(self):
        read_group_res = self.env["ir.attachment"]._read_group(
            [("res_model", "=", "hr.applicant"), ("res_id", "in", self.ids)],
            ["res_id"],
            ["__count"],
        )
        attach_data = dict(read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        job_id = self.env.context.get("default_job_id")
        search_domain = [("job_ids", "=", False)]
        if job_id:
            search_domain = ["|", ("job_ids", "=", job_id)] + search_domain
        if stages:
            search_domain = ["|", ("id", "in", stages.ids)] + search_domain

        stage_ids = stages.sudo()._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    @api.depends("job_id", "department_id")
    def _compute_company_id(self):
        for applicant in self:
            company_id = False
            if applicant.department_id:
                company_id = applicant.department_id.company_id.id
            if not company_id and applicant.job_id:
                company_id = applicant.job_id.company_id.id
            applicant.company_id = company_id or self.env.company.id

    @api.depends("job_id")
    def _compute_department_id(self):
        for applicant in self:
            applicant.department_id = applicant.job_id.department_id.id

    @api.depends("job_id")
    def _compute_stage_id(self):
        without_job = self.filtered(lambda a: not a.job_id)
        without_job.stage_id = False
        to_assign = (self - without_job).filtered(lambda a: not a.stage_id)
        if not to_assign:
            return
        first_stage_by_job = self.env["hr.recruitment.stage"]._get_first_stage_by_job(
            to_assign.job_id
        )
        _debug.logic(
            "first_stage_assigned", applicants=to_assign, jobs=to_assign.job_id
        )
        for applicant in to_assign:
            applicant.stage_id = first_stage_by_job[applicant.job_id]

    @api.depends("job_id")
    def _compute_user_id(self):
        for applicant in self:
            applicant.user_id = applicant.job_id.user_id.id

    @api.depends("stage_id.hired_stage")
    def _compute_date_closed(self):
        now = fields.Datetime.now()
        for applicant in self:
            if applicant.stage_id.hired_stage:
                applicant.date_closed = applicant.date_closed or now
            else:
                applicant.date_closed = False

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)

        if not self.env.context.get("no_copy_in_partner_name"):
            vals_list = [
                dict(vals, partner_name=self.env._("%s (copy)", applicant.partner_name))
                for applicant, vals in zip(self, vals_list, strict=True)
            ]
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("user_id"):
                vals["date_open"] = fields.Datetime.now()
            if vals.get("email_from"):
                vals["email_from"] = vals["email_from"].strip()
        applicants = super().create(vals_list)
        _debug.lifecycle("create", applicants=applicants, count=len(vals_list))
        applicants.sudo().interviewer_ids._create_recruitment_interviewers()

        for applicant in applicants:
            if applicant.talent_pool_ids and not applicant.pool_applicant_id:
                applicant.pool_applicant_id = applicant
            applicant._notify_interviewers(applicant.interviewer_ids)
        return applicants

    def _notify_interviewers(self, interviewers):
        self.check_singleton()
        partners = interviewers.partner_id - self.env.user.partner_id
        if not partners:
            return
        _debug.pipeline("interviewers_notified", applicant=self, partners=partners)
        self.message_notify(
            partner_ids=partners.ids,
            author_id=self.env.user.partner_id.id,
            email_from=self.env.user.email_formatted,
            subject=_(
                "You have been assigned as an interviewer for %s", self.display_name
            ),
            body=_(
                "You have been assigned as an interviewer for the Applicant %s",
                self.partner_name,
            ),
            email_layout_xmlid="mail.mail_notification_layout",
            model_description="Applicant",
        )

    def write(self, vals):
        if vals.get("user_id"):
            vals["date_open"] = fields.Datetime.now()
        old_interviewers = self.interviewer_ids
        applicants_by_old_stage = {}
        _debug.lifecycle("write", applicants=self, fields=list(vals))
        if "stage_id" in vals:
            new_stage = self.env["hr.recruitment.stage"].browse(vals["stage_id"])
            moving = self.filtered(lambda a: a.stage_id != new_stage)
            _debug.logic(
                "stage_write", applicants=self, moving=moving, new_stage=new_stage
            )
            if moving:
                vals["date_last_stage_update"] = fields.Datetime.now()
                vals.setdefault("kanban_state", "normal")
                moving._update_job_recruitment_target(new_stage)
                applicants_by_old_stage = moving.grouped("stage_id")
                if moving == self and len(applicants_by_old_stage) == 1:
                    vals["last_stage_id"] = next(iter(applicants_by_old_stage)).id
                    applicants_by_old_stage = {}
        if "kanban_state" in vals:
            vals["date_last_stage_update"] = fields.Datetime.now()
        res = super().write(vals)
        for old_stage, applicants in applicants_by_old_stage.items():
            super(HrApplicant, applicants).write({"last_stage_id": old_stage.id})

        talent_vals = {
            fname: vals[fname]
            for fname in (
                "email_from",
                "phone_ids",
                "linkedin_profile",
                "degree_id",
            )
            if fname in vals
        }
        if talent_vals:
            _debug.pipeline("talent_sync", applicants=self, fields=list(talent_vals))
            for applicant in self:
                talent = applicant.pool_applicant_id
                if talent and talent != applicant and not applicant.is_pool_applicant:
                    talent.write(talent_vals)

        if "interviewer_ids" in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            _debug.lifecycle(
                "interviewers_changed",
                applicants=self,
                removed=interviewers_to_clean,
                kept=self.interviewer_ids,
            )
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()
            new_interviewers = self.interviewer_ids - old_interviewers
            for applicant in self:
                applicant._notify_interviewers(new_interviewers)
        return res

    def _update_job_recruitment_target(self, new_stage):
        delta_by_job = defaultdict(int)
        for applicant in self:
            was_hired = applicant.stage_id.hired_stage
            if new_stage.hired_stage and not was_hired:
                delta_by_job[applicant.job_id] -= 1
            elif was_hired and not new_stage.hired_stage:
                delta_by_job[applicant.job_id] += 1
        for job, delta in delta_by_job.items():
            if job and delta:
                _debug.lifecycle(
                    "recruitment_target_moved",
                    job=job,
                    delta=delta,
                    was=job.no_of_recruitment,
                )
                job.no_of_recruitment = max(0, job.no_of_recruitment + delta)

    @api.model
    def get_empty_list_help(self, help_message):
        if (
            "active_id" in self.env.context
            and self.env.context.get("active_model") == "hr.job"
        ):
            hr_job = self.env["hr.job"].browse(self.env.context["active_id"])
        elif self.env.context.get("default_job_id"):
            hr_job = self.env["hr.job"].browse(self.env.context["default_job_id"])
        else:
            hr_job = self.env["hr.job"]

        nocontent_body = Markup("""
<p class="o_view_nocontent_smiling_face">%(help_title)s</p>
""") % {
            "help_title": _("No applications found."),
        }

        if hr_job.alias_email:
            nocontent_body += Markup(
                '<p class="o_copy_paste_email oe_view_nocontent_alias">%(helper_email)s <a href="mailto:%(email)s">%(email)s</a></p>'
            ) % {
                "helper_email": _("Send applications to"),
                "email": hr_job.alias_email,
            }

        return super().get_empty_list_help(nocontent_body)

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        if view_type == "form" and self.env.user._is_recruitment_interviewer_only():
            view_id = self.env.ref(
                "hr_recruitment.hr_applicant_view_form_interviewer"
            ).id
        return super().get_view(view_id, view_type, **options)

    def _get_or_create_partner(self):
        self.check_singleton()
        if self.partner_id:
            return self.partner_id
        if not self.partner_name:
            _debug.logic("partner_refused", reason="no_contact_name", applicant=self)
            raise UserError(_("You must define a Contact Name for this applicant."))
        _debug.lifecycle("partner_created_for_applicant", applicant=self)
        self.partner_id = self.env["res.partner"].create(
            {
                "is_company": False,
                "name": self.partner_name,
                "email": self.email_from,
                "phone_ids": [Command.set(self.phone_ids.ids)],
            }
        )
        return self.partner_id

    def action_create_meeting(self):
        self._get_or_create_partner()
        partners = self.partner_id | self.department_id.manager_id.user_id.partner_id
        if self.env.user._is_recruitment_interviewer_only():
            partners |= self.env.user.partner_id
        else:
            partners |= self.user_id.partner_id

        res = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "calendar.action_calendar_event"
        )
        res["context"] = {
            "create": True,
            "default_applicant_id": self.id,
            "default_partner_ids": partners.ids,
            "default_user_id": self.env.uid,
            "default_name": self.partner_name,
        }
        return res

    def action_view_attachments(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "name": _("Documents"),
            "context": {
                "default_res_model": "hr.applicant",
                "default_res_id": self.ids[0],
                "show_partner_name": 1,
            },
            "view_mode": "list,form",
            "views": [
                (
                    self.env.ref(
                        "hr_recruitment.ir_attachment_hr_recruitment_list_view"
                    ).id,
                    "list",
                ),
                (False, "form"),
            ],
            "search_view_id": self.env.ref(
                "hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment"
            ).ids,
            "domain": [
                ("res_model", "=", "hr.applicant"),
                ("res_id", "in", self.ids),
            ],
        }

    def action_view_employee(self):
        self.check_singleton()
        return {
            "name": _("Employee"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "form",
            "res_id": self.employee_id.id,
        }

    def action_view_applications(self):
        self.check_singleton()
        similar_applicants = (
            self.env["hr.applicant"]
            .with_context(active_test=False)
            .search(
                self._get_domain_similar_applicants(ignore_talent=True),
            )
        )
        return {
            "name": _("Applications"),
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "list,form",
            "domain": [("id", "in", similar_applicants.ids)],
            "context": {
                "active_test": False,
                "search_default_stage": 1,
                "default_applicant_ids": self.ids,
                "no_create_application_button": True,
            },
        }

    def action_talent_pool_stat_button(self):
        self.check_singleton()
        if not self.pool_applicant_id:
            self.link_applicant_to_talent()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "form",
            "target": "current",
            "res_id": self.pool_applicant_id.id,
        }

    def link_applicant_to_talent(self):
        talent = self.env["hr.applicant"].search(
            domain=self._get_domain_similar_applicants(only_talent=True),
            order="id",
            limit=1,
        )
        self.pool_applicant_id = talent

    def action_talent_pool_add_applicants(self):
        return {
            "name": _("Add applicant(s) to the pool"),
            "type": "ir.actions.act_window",
            "res_model": "talent.pool.add.applicants",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "is_modal": True,
                "dialog_size": "medium",
                "default_talent_pool_ids": self.env.context.get(
                    "default_talent_pool_ids"
                )
                or [],
                "default_applicant_ids": self.ids,
            },
        }

    def action_job_add_applicants(self):
        return {
            "name": _("Create Applications"),
            "type": "ir.actions.act_window",
            "res_model": "job.add.applicants",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "is_modal": True,
                "dialog_size": "medium",
                "default_applicant_ids": self.ids
                or self.env.context.get("default_applicant_ids"),
            },
        }

    def _track_template(self, changes):
        res = super()._track_template(changes)
        applicant = self[0]
        if (
            "stage_id" in changes
            and applicant.exists()
            and applicant.stage_id.template_id
            and not applicant.env.context.get("just_moved")
            and not applicant.env.context.get("just_unarchived")
        ):
            res["stage_id"] = (
                applicant.stage_id.template_id,
                {
                    "auto_delete_keep_log": False,
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_note"
                    ),
                    "email_layout_xmlid": "hr_recruitment.mail_notification_light_without_background",
                },
            )
        return res

    def _creation_subtype(self):
        self.check_singleton()
        if self.is_pool_applicant:
            return self.env.ref("hr_recruitment.mt_talent_new")
        return self.env.ref("hr_recruitment.mt_applicant_new")

    def _track_subtype(self, init_values):
        record = self[0]
        if "stage_id" in init_values and record.stage_id:
            return self.env.ref("hr_recruitment.mt_applicant_stage_changed")
        return super()._track_subtype(init_values)

    def _notify_get_reply_to_addresses(self):
        addresses = self.mapped("job_id")._notify_get_reply_to_addresses()
        res = {
            app.id: addresses[app.job_id.id]
            for app in self
            if app.job_id and app.job_id.id in addresses
        }
        leftover = self.filtered(lambda rec: not rec.job_id)
        if leftover:
            res.update(super(HrApplicant, leftover)._notify_get_reply_to_addresses())
        return res

    def _mail_get_customer_information(self):
        email_keys_to_values = super()._mail_get_customer_information()

        for applicant in self:
            email_key = (
                tools.email_normalize(applicant.email_from) or applicant.email_from
            )
            if not email_key and len(self) > 1:
                continue
            email_keys_to_values.setdefault(email_key, {}).update(
                {
                    "name": applicant.partner_name
                    or tools.parse_contact_from_email(applicant.email_from)[0]
                    or applicant.email_from,
                    "phone_ids": [Command.set(applicant.phone_ids.ids)],
                }
            )
        return email_keys_to_values

    @api.depends("partner_name")
    @api.depends_context("show_partner_name")
    def _compute_display_name(self):
        if not self.env.context.get("show_partner_name"):
            return super()._compute_display_name()
        for applicant in self:
            applicant.display_name = applicant.partner_name
        return None

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        self = self.with_context(default_user_id=False)
        partner_name, email_from_normalized = tools.parse_contact_from_email(
            msg_dict.get("from")
        )
        defaults = {"partner_name": partner_name}
        job_platform = (
            self.env["hr.job.platform"]
            .sudo()
            .search([("email", "=", email_from_normalized)], limit=1)
        )
        if job_platform:
            if job_platform.regex:
                pattern = re.compile(job_platform.regex)
                matches = pattern.findall(
                    msg_dict.get("subject") or ""
                ) + pattern.findall(msg_dict.get("body") or "")
                if matches:
                    defaults["partner_name"] = matches[0]
            msg_dict.pop("email_from", None)
        elif msg_dict.get("from"):
            defaults["email_from"] = msg_dict["from"]
            defaults["partner_id"] = msg_dict.get("author_id", False)
        if msg_dict.get("priority"):
            defaults["priority"] = msg_dict["priority"]
        if custom_values:
            defaults.update(custom_values)
        _debug.pipeline(
            "message_new",
            platform=job_platform.name or "-",
            regex_matched=bool(
                job_platform and job_platform.regex and defaults.get("partner_name")
            ),
            partner_name=defaults.get("partner_name") or "-",
            has_email=bool(defaults.get("email_from")),
        )
        applicant = super().message_new(msg_dict, custom_values=defaults)
        # The mail carries an address but no number, so take the contact's --
        # previously done by calling `_compute_partner_phone_email` directly,
        # which also rewrote `email_from` from the contact and so could replace
        # the address the applicant actually wrote from.
        if applicant.partner_id and not applicant.phone_ids:
            _debug.logic(
                "phones_from_contact",
                applicant=applicant,
                partner=applicant.partner_id,
            )
            applicant.phone_ids = applicant.partner_id.phone_ids
        return applicant

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            email_normalized = tools.email_normalize(self.email_from)
            new_partner = message.partner_ids.filtered(
                lambda partner: (
                    partner.email == self.email_from
                    or (
                        email_normalized
                        and partner.email_normalized == email_normalized
                    )
                )
            )
            if new_partner:
                if new_partner[0].create_date.date() == fields.Date.today():
                    new_partner[0].write(
                        {
                            "name": self.partner_name or self.email_from,
                        }
                    )
                if new_partner[0].email_normalized:
                    email_domain = (
                        "email_from",
                        "in",
                        [new_partner[0].email, new_partner[0].email_normalized],
                    )
                else:
                    email_domain = ("email_from", "=", new_partner[0].email)
                self.search(
                    [
                        ("partner_id", "=", False),
                        email_domain,
                        ("stage_id.fold", "=", False),
                    ]
                ).write({"partner_id": new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    def create_employee_from_applicant(self):
        self.check_singleton()
        self._check_interviewer_access()
        self._get_or_create_partner()

        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "hr.open_view_employee_list"
        )
        employee = (
            self.env["hr.employee"]
            .with_context(clean_context(self.env.context))
            .create(self._prepare_employee_vals())
        )
        action["res_id"] = employee.id
        _debug.lifecycle(
            "employee_created",
            applicant=self,
            employee=employee.id,
            attachments=len(self.attachment_ids),
        )
        self.attachment_ids.copy({"res_model": "hr.employee", "res_id": employee.id})
        return action

    def _prepare_employee_vals(self):
        self.check_singleton()
        address_id = self.partner_id.address_get(["contact"])["contact"]
        address_sudo = self.env["res.partner"].sudo().browse(address_id)
        return {
            "name": self.partner_name or self.partner_id.display_name,
            "partner_id": self.partner_id.id,
            "job_id": self.job_id.id,
            "job_title": self.job_id.name,
            "private_street": address_sudo.street,
            "private_street2": address_sudo.street2,
            "private_city": address_sudo.city,
            "private_state_id": address_sudo.state_id.id,
            "private_zip": address_sudo.zip,
            "private_country_id": address_sudo.country_id.id,
            "private_phone_ids": [Command.set(address_sudo.phone_ids.ids)],
            "private_email": address_sudo.email,
            "lang": address_sudo.lang,
            "department_id": self.department_id.id,
            "address_id": self.company_id.partner_id.id,
            "work_email": self.department_id.company_id.email or self.email_from,
            "applicant_ids": self.ids,
        }

    def _check_interviewer_access(self):
        if self.env.user._is_recruitment_interviewer_only():
            raise UserError(_("You are not allowed to perform this action."))

    def archive_applicant(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Refuse Reason"),
            "res_model": "applicant.get.refuse.reason",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_applicant_ids": self.ids,
                "active_test": False,
                "hide_mail_template_management_options": True,
            },
            "views": [[False, "form"]],
        }

    def reset_applicant(self):
        """Send applications back to the start of their job's flow.

        Grouped by job because the target stage is per job, so this costs one
        write per distinct job rather than one per application.
        """
        Stage = self.env["hr.recruitment.stage"]
        first_stage_by_job = Stage._get_first_stage_by_job(self.job_id)
        for job, applicants in self.grouped("job_id").items():
            applicants.write(
                {
                    "stage_id": first_stage_by_job.get(job, Stage).id,
                    "refuse_reason_id": False,
                    "refuse_date": False,
                    "archived_with_job": False,
                }
            )

    def action_archive(self):
        return super(
            HrApplicant, self.with_context(just_unarchived=True)
        ).action_archive()

    def action_unarchive(self):
        res = super(
            HrApplicant, self.with_context(just_unarchived=True)
        ).action_unarchive()
        self.reset_applicant()
        return res

    def action_send_email(self):
        return {
            "name": _("Send Email"),
            "type": "ir.actions.act_window",
            "target": "new",
            "view_mode": "form",
            "res_model": "applicant.send.mail",
            "context": {
                "default_applicant_ids": self.ids,
            },
        }

    def _get_duration_from_tracking(self, trackings):
        """Stop the current stage's clock at the moment of refusal.

        ``super()`` counts every stage up to now; a refused application stopped
        moving when it was refused, so the span since then is not time spent in
        the stage. Clamped at zero: a ``refuse_date`` older than the stage entry
        would otherwise report a negative duration that grows every day.
        """
        durations = super()._get_duration_from_tracking(trackings)
        if self.refuse_reason_id and self.refuse_date:
            stage_id = self.stage_id.id
            since_refusal = (self.env.cr.now() - self.refuse_date).total_seconds()
            durations[stage_id] = max(0, durations.get(stage_id, 0) - since_refusal)
        return durations

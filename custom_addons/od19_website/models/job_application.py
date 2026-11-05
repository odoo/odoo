import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Od19JobApplication(models.Model):
    """An application (candidate) submitted for a job opening.

    A candidate either applies for a specific published position
    (``application_type == "specific"``) or sends a general / speculative
    application expressing the wish to join the company
    (``application_type == "speculative"``); in the latter case ``job_id``
    is empty and ``applied_position`` carries the free-text role.
    """

    _name = "od19.job.application"
    _description = "Job Application"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    application_type = fields.Selection(
        selection=[
            ("specific", "Application for a Position"),
            ("speculative", "General / Speculative Application"),
        ],
        string="Application Type",
        default="specific",
        required=True,
        tracking=True,
    )

    job_id = fields.Many2one(
        "od19.job.opening",
        string="Job Position",
        ondelete="cascade",
        tracking=True,
    )
    applied_position = fields.Char(
        string="Position Applied For",
        help="Free text used for general applications, e.g. 'Automation Engineer'.",
        tracking=True,
    )
    department = fields.Selection(
        related="job_id.department", string="Department", store=True
    )
    preferred_department = fields.Selection(
        selection=[
            ("industrial", "Industrial Automation"),
            ("building", "Building Automation"),
            ("terminal", "Terminal Automation"),
            ("support", "Sales & Administration"),
        ],
        string="Preferred Department",
        help="Used for general applications when no specific position is chosen.",
    )
    reference = fields.Char(string="Reference", readonly=True, copy=False)

    # --- Candidate details -------------------------------------------------
    name = fields.Char(string="Full Name", required=True, tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Phone")
    current_company = fields.Char(string="Current Company")
    current_position = fields.Char(string="Current Position")
    years_experience = fields.Float(string="Years of Experience")
    education_level = fields.Selection(
        selection=[
            ("vocational", "Vocational Certificate / Diploma"),
            ("bachelor", "Bachelor's Degree"),
            ("master", "Master's Degree"),
            ("doctorate", "Doctorate"),
        ],
        string="Highest Education",
    )
    expected_salary = fields.Char(string="Expected Salary")
    notice_period = fields.Char(
        string="Notice Period",
        help="e.g. '30 days', 'Immediately available'.",
    )
    available_date = fields.Date(string="Available From")
    preferred_location = fields.Char(string="Preferred Work Location")
    willing_to_travel = fields.Boolean(string="Willing to Travel / Work on Site")
    portfolio_url = fields.Char(
        string="LinkedIn / Portfolio URL",
        help="Link to a LinkedIn profile, portfolio or personal website.",
    )
    source = fields.Char(
        string="How did you hear about us?",
        help="e.g. JobThai, LinkedIn, Referral ...",
    )
    cover_letter = fields.Text(string="Cover Letter / Message")

    # --- Documents ---------------------------------------------------------
    resume = fields.Binary(
        string="Resume / CV",
        attachment=True,
        help="Main resume or curriculum vitae of the candidate.",
    )
    resume_filename = fields.Char(string="Resume Filename")
    document_ids = fields.Many2many(
        "ir.attachment",
        "od19_job_application_ir_attachment_rel",
        "application_id",
        "attachment_id",
        string="Supporting Documents",
        help="Transcripts, certificates, portfolio and other supporting files.",
    )
    document_count = fields.Integer(
        string="Documents", compute="_compute_document_count"
    )

    # --- Consent (PDPA evidence) ------------------------------------------
    consent_privacy = fields.Boolean(
        string="Privacy Consent Given",
        help="Set when the applicant accepted the recruitment privacy notice.",
    )
    consent_date = fields.Datetime(string="Consent Given On", readonly=True)

    # --- Recruitment workflow ---------------------------------------------
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("shortlisted", "Shortlisted"),
            ("interview", "Interview"),
            ("offer", "Offer Sent"),
            ("hired", "Hired"),
            ("refused", "Not Selected"),
        ],
        string="Status",
        default="new",
        tracking=True,
        group_expand="_group_expand_state",
    )
    note = fields.Text(string="Internal Notes")

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("document_ids")
    def _compute_document_count(self):
        for application in self:
            application.document_count = len(application.document_ids)

    @api.depends("job_id", "applied_position")
    def _compute_display_name(self):
        for application in self:
            position = application.job_id.name or application.applied_position
            application.display_name = (
                "%s - %s" % (application.name, position)
                if position
                else application.name
            )

    @api.model
    def _group_expand_state(self, states, domain):
        return [key for key, _label in self._fields["state"].selection]

    # ------------------------------------------------------------------
    # Create / notifications
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference") or vals.get("reference") == self.env._("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "od19.job.application"
                ) or self.env._("New")
        applications = super().create(vals_list)
        for application in applications:
            application._od19_notify_new_application()
        return applications

    def _od19_notify_new_application(self):
        """Email the recruitment team and acknowledge the applicant.

        Both templates are optional: the code stays silent when they are not
        installed yet so a missing template never blocks an application.
        """
        for application in self:
            for xmlid in (
                "od19_website.mail_template_job_application_hr",
                "od19_website.mail_template_job_application_ack",
            ):
                template = self.env.ref(xmlid, raise_if_not_found=False)
                if not template:
                    continue
                try:
                    template.send_mail(application.id, force_send=False)
                except Exception:  # noqa: BLE001 - never block the application
                    _logger.exception(
                        "Could not send recruitment email %s for application %s.",
                        xmlid,
                        application.id,
                    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def department_label(self):
        """Human readable department, falling back to the preferred one."""
        self.ensure_one()
        key = self.department or self.preferred_department
        return dict(self._fields["preferred_department"].selection).get(key, "")

    def position_label(self):
        """Position the candidate applied for."""
        self.ensure_one()
        return self.job_id.name or self.applied_position or ""

    # ------------------------------------------------------------------
    # Recruitment workflow
    # ------------------------------------------------------------------
    def action_shortlist(self):
        self.write({"state": "shortlisted"})

    def action_interview(self):
        self.write({"state": "interview"})

    def action_offer(self):
        self.write({"state": "offer"})

    def action_hired(self):
        self.write({"state": "hired"})

    def action_refuse(self):
        self.write({"state": "refused"})

    def action_reset(self):
        self.write({"state": "new"})

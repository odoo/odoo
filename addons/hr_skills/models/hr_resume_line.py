from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import normalize_url

_debug = DebugLog(__name__)


class HrResumeLine(models.Model):
    _name = "hr.resume.line"
    _description = "Resume line of an employee"
    _order = "line_type_id, date_end desc, date_start desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        index=True,
        required=True,
        ondelete="cascade",
    )
    avatar_128 = fields.Image(related="employee_id.avatar_128")
    company_id = fields.Many2one(related="employee_id.company_id")
    department_id = fields.Many2one(related="employee_id.department_id")
    name = fields.Char(
        translate=True,
        required=True,
    )
    date_start = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    date_end = fields.Date()
    duration = fields.Integer()
    description = fields.Html(translate=True)
    line_type_id = fields.Many2one(
        comodel_name="hr.resume.line.type",
        string="Type",
    )
    is_course = fields.Boolean(related="line_type_id.is_course")
    course_type = fields.Selection(
        selection=[("external", "External")],
        default="external",
        required=True,
    )
    color = fields.Char(compute="_compute_color")
    external_url = fields.Char(
        string="External URL",
        compute="_compute_external_url",
        store=True,
        readonly=False,
    )
    certificate_filename = fields.Char()
    certificate_file = fields.Binary(string="Certificate")
    resume_line_properties = fields.Properties(
        definition="line_type_id.resume_line_type_properties_definition",
        string="Properties",
    )

    _date_check = models.Constraint(
        "CHECK ((date_start <= date_end OR date_end IS NULL))",
        "The start date must be anterior to the end date.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_external_url(vals)
        _debug.lifecycle("resume_lines_created", count=len(vals_list))
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_external_url(vals)
        _debug.lifecycle("resume_line_write", lines=self, fields=list(vals))
        return super().write(vals)

    @staticmethod
    def _normalize_external_url(vals):
        if url := (vals.get("external_url") or "").strip():
            vals["external_url"] = normalize_url(url)

    @api.onchange("external_url")
    def _onchange_external_url(self):
        if not self.name and self.external_url:
            self.name = self._site_name(self.external_url)

    @api.model
    def _site_name(self, url):
        """The registrable label of the URL's host, capitalised, or nothing.

        ``https://docs.python.org/3/`` -> ``Python``; a bare ``coursera.org``
        counts too. The regex this replaces stopped at the *last* dot of the
        whole URL, so any path holding a dot gave ``Example.com/a.b``."""
        if "//" not in url:
            url = f"//{url}"
        host = urlsplit(url).hostname or ""
        labels = [label for label in host.split(".") if label]
        if labels and labels[0] == "www":
            labels = labels[1:]
        if not labels:
            return False
        return (labels[-2] if len(labels) >= 2 else labels[0]).capitalize()

    @api.depends("course_type")
    def _compute_external_url(self):
        for resume_line in self:
            if resume_line.course_type != "external":
                resume_line.external_url = ""

    @api.depends("course_type")
    def _compute_color(self):
        for resume_line in self:
            resume_line.color = (
                "#a2a2a2" if resume_line.course_type == "external" else "#000000"
            )

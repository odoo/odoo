import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AwRule(models.Model):
    _name = "aw.rule"
    _description = "ActivityWatch Browser URL Rule"
    _order = "sequence"

    name = fields.Char(required=True)
    regex = fields.Char(required=True)
    type = fields.Selection(
        [
            ("reading_emails", "Reading Emails"),
            ("writing_emails", "Writing Emails"),
            ("video_conference", "Video Conference"),
            ("communication", "Communication"),
            ("meeting", "Meeting"),
            ("odoo", "Odoo"),
            ("word", "Word"),
            ("excel", "Excel"),
            ("powerpoint", "PowerPoint"),
        ],
        required=True,
    )
    template = fields.Char()
    project_id = fields.Many2one(
        "project.project", string="Project",
        compute="_compute_project_id", inverse="_inverse_project_id",
        store=True, readonly=False,
    )
    task_id = fields.Many2one("project.task", domain="[('project_id', '=?', project_id)]", string="Task")
    always_active = fields.Boolean(default=False)
    primary = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    match_count = fields.Integer(
        string="Capture Groups", compute="_compute_match_count", default=0,
    )

    @api.depends("task_id")
    def _compute_project_id(self):
        for rule in self:
            if rule.task_id:
                rule.project_id = rule.task_id.project_id

    def _inverse_project_id(self):
        for rule in self:
            if rule.task_id and rule.task_id.project_id != rule.project_id:
                rule.task_id = False

    @api.depends("regex")
    def _compute_match_count(self):
        for record in self:
            if not record.regex:
                continue

            try:
                pattern = re.compile(record.regex)
                record.match_count = pattern.groups
            except re.error:
                record.match_count = 0

    @api.constrains("regex")
    def _check_regex(self):
        for record in self:
            try:
                re.compile(record.regex)
            except re.error:
                raise ValidationError(self.env._("Invalid regex: %(regex)s", regex=record.regex))

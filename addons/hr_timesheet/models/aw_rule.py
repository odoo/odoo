from odoo import models, fields, api
import re

class AwRule(models.Model):
    _name = "aw.rule"
    _description = "ActivityWatch Browser URL Rule"
    _order = "sequence"

    name = fields.Char(required=True)
    regex = fields.Char(required=True)
    type = fields.Selection([
        ("reading_emails", "Reading Emails"),
        ("writing_emails", "Writing Emails"),
        ("video_conference", "Video Conference"),
        ("communication", "Communication"),
        ("meeting", "Meeting"),
        ("odoo", "Odoo"),
        ("word", "Word"),
        ("excel", "Excel"),
        ("powerpoint", "PowerPoint")
    ], required=True)
    template = fields.Char()
    project_id = fields.Many2one("project.project", string="Project")
    task_id = fields.Many2one("project.task", string="Task")
    always_active = fields.Boolean(default=False)
    primary = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)
    match_count = fields.Integer(string="Capture Groups", compute="_compute_match_count", default=0)

    @api.depends("regex")
    def _compute_match_count(self):
        for record in self:
            if record.regex == False:
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
                raise models.ValidationError(f"Invalid regex: {record.regex}")

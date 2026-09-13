from odoo import api, fields, models


class HrResumeLine(models.Model):
    _inherit = "hr.resume.line"

    channel_id = fields.Many2one(
        comodel_name="slide.channel",
        string="eLearning Course",
        compute="_compute_channel_id",
        store=True,
        index="btree_not_null",
        readonly=True,
    )
    course_url = fields.Char(related="channel_id.website_absolute_url")
    duration = fields.Integer(
        compute="_compute_duration",
        store=True,
        readonly=False,
    )
    course_type = fields.Selection(
        selection_add=[("elearning", "eLearning")],
        ondelete={"elearning": "cascade"},
    )

    @api.depends("channel_id")
    def _compute_duration(self):
        for resume_line in self:
            resume_line.duration = resume_line.channel_id.total_time

    @api.onchange("channel_id")
    def _onchange_channel_id(self):
        if not self.name and self.channel_id:
            self.name = self.channel_id.name

    @api.depends("course_type")
    def _compute_channel_id(self):
        for resume_line in self:
            if resume_line.course_type != "elearning":
                resume_line.channel_id = False

    def _compute_color(self):
        super()._compute_color()
        for resume_line in self:
            if resume_line.course_type == "elearning":
                resume_line.color = "#00a5b7"

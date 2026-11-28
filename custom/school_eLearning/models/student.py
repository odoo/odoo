# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniversityStudent(models.Model):
    _inherit = "university.student"

    slide_channel_ids = fields.Many2many(
        "slide.channel",
        string="eLearning Courses",
        compute="_compute_slide_channels",
        help="eLearning courses available to this student via active section enrollments.",
    )
    slide_channel_count = fields.Integer(
        string="eLearning Courses Count",
        compute="_compute_slide_channels",
    )

    @api.depends("enrollment_ids.status", "enrollment_ids.class_section_id.slide_channel_ids")
    def _compute_slide_channels(self):
        for student in self:
            enrolled_sections = student.enrollment_ids.filtered(lambda e: e.status == "enrolled").mapped("class_section_id")
            channels = enrolled_sections.mapped("slide_channel_ids")
            student.slide_channel_ids = channels
            student.slide_channel_count = len(channels)

    def action_view_slide_channels(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("website_slides.slide_channel_action_overview")
        action["domain"] = [("id", "in", self.slide_channel_ids.ids)]
        return action

# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniversityClassSection(models.Model):
    _inherit = "university.class.section"

    slide_channel_ids = fields.One2many(
        "slide.channel",
        "class_section_id",
        string="eLearning Courses",
        help="Online eLearning courses assigned to this section.",
    )
    slide_channel_count = fields.Integer(
        string="eLearning Courses Count",
        compute="_compute_slide_channel_count",
    )

    @api.depends("slide_channel_ids")
    def _compute_slide_channel_count(self):
        for section in self:
            section.slide_channel_count = len(section.slide_channel_ids)

    def action_view_slide_channels(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("website_slides.slide_channel_action_overview")
        action["domain"] = [("class_section_id", "=", self.id)]
        action["context"] = {
            "default_class_section_id": self.id,
            "default_subject_id": self.subject_id.id if self.subject_id else False,
            "default_teacher_id": self.primary_teacher_id.id if hasattr(self, "primary_teacher_id") and self.primary_teacher_id else False,
        }
        return action

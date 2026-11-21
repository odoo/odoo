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

    def write(self, vals):
        res = super().write(vals)
        if "teacher_id" in vals:
            for section in self:
                if section.slide_channel_ids:
                    update_vals = {
                        "teacher_id": section.teacher_id.id if section.teacher_id else False,
                    }
                    if section.teacher_id and section.teacher_id.user_id:
                        update_vals["user_id"] = section.teacher_id.user_id.id
                    section.slide_channel_ids.write(update_vals)
        if "subject_id" in vals:
            for section in self:
                if section.slide_channel_ids:
                    section.slide_channel_ids.write({
                        "subject_id": section.subject_id.id if section.subject_id else False,
                    })
        return res

    def action_view_slide_channels(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("website_slides.slide_channel_action_overview")
        action["domain"] = [("class_section_id", "=", self.id)]
        action["context"] = {
            "default_class_section_id": self.id,
            "default_subject_id": self.subject_id.id if self.subject_id else False,
            "default_teacher_id": self.teacher_id.id if self.teacher_id else False,
        }
        return action

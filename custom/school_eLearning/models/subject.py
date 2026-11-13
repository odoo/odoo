# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniversitySubject(models.Model):
    _inherit = "university.subject"

    slide_channel_ids = fields.One2many(
        "slide.channel",
        "subject_id",
        string="eLearning Courses",
        help="Online eLearning courses linked to this subject.",
    )
    slide_channel_count = fields.Integer(
        string="eLearning Courses Count",
        compute="_compute_slide_channel_count",
    )

    @api.depends("slide_channel_ids")
    def _compute_slide_channel_count(self):
        for subject in self:
            subject.slide_channel_count = len(subject.slide_channel_ids)

    def action_view_slide_channels(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("website_slides.slide_channel_action_overview")
        action["domain"] = [("subject_id", "=", self.id)]
        action["context"] = {
            "default_subject_id": self.id,
            "default_name": self.name,
        }
        return action

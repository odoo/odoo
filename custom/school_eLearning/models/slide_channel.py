# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    subject_id = fields.Many2one(
        "university.subject",
        string="University Subject",
        index=True,
        help="Academic subject this eLearning course is associated with.",
    )
    teacher_id = fields.Many2one(
        "university.teacher",
        string="Instructor / Teacher",
        domain="[('active', '=', True)]",
        help="University teacher responsible for this course content.",
    )
    class_section_id = fields.Many2one(
        "university.class.section",
        string="Class Section",
        help="Specific class section enrolled in this course channel.",
    )

    @api.onchange("class_section_id")
    def _onchange_class_section_id(self):
        if self.class_section_id and not self.subject_id:
            self.subject_id = self.class_section_id.subject_id
        if self.class_section_id and hasattr(self.class_section_id, "primary_teacher_id") and self.class_section_id.primary_teacher_id and not self.teacher_id:
            self.teacher_id = self.class_section_id.primary_teacher_id

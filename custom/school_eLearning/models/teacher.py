# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UniversityTeacher(models.Model):
    _inherit = "university.teacher"

    slide_channel_ids = fields.One2many(
        "slide.channel",
        "teacher_id",
        string="eLearning Courses",
        help="eLearning courses instructed by this teacher.",
    )
    slide_channel_count = fields.Integer(
        string="eLearning Courses Count",
        compute="_compute_slide_channel_count",
    )

    @api.depends("slide_channel_ids")
    def _compute_slide_channel_count(self):
        for rec in self:
            rec.slide_channel_count = len(rec.slide_channel_ids)

    def action_view_slide_channels(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'eLearning Courses',
            'res_model': 'slide.channel',
            'view_mode': 'list,form',
            'domain': [('teacher_id', '=', self.id)],
            'context': {'default_teacher_id': self.id},
        }

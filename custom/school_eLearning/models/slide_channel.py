# -*- coding: utf-8 -*-
# custom/school_eLearning/models/slide_channel.py
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

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
        index=True,
        help="Specific class section enrolled in this course channel.",
    )
    section_student_count = fields.Integer(
        string="Section Students",
        compute="_compute_section_student_count",
        help="Number of students actively enrolled in the assigned class section.",
    )

    @api.depends("class_section_id", "class_section_id.enrollment_ids.status")
    def _compute_section_student_count(self):
        for channel in self:
            if channel.class_section_id:
                channel.section_student_count = len(
                    channel.class_section_id.enrollment_ids.filtered(lambda e: e.status == "enrolled")
                )
            else:
                channel.section_student_count = 0

    @api.onchange('class_section_id')
    def _onchange_class_section_id(self):
        section = self.class_section_id
        if section:
            if section.subject_id:
                self.subject_id = section.subject_id
            if section.teacher_id:
                self.teacher_id = section.teacher_id
            if not self.user_id and section.teacher_id and section.teacher_id.user_id:
                self.user_id = section.teacher_id.user_id

    @api.onchange('teacher_id')
    def _onchange_teacher_id(self):
        if self.teacher_id:
            if not self.user_id and self.teacher_id.user_id:
                self.user_id = self.teacher_id.user_id
            if not self.subject_id and len(self.teacher_id.subject_ids) == 1:
                self.subject_id = self.teacher_id.subject_ids[0]

    @api.onchange('subject_id')
    def _onchange_subject_id(self):
        if self.subject_id and self.class_section_id:
            if self.class_section_id.subject_id and self.class_section_id.subject_id != self.subject_id:
                self.class_section_id = False
        if self.subject_id and self.teacher_id:
            if self.teacher_id.subject_ids and self.subject_id not in self.teacher_id.subject_ids:
                self.teacher_id = False

    @api.constrains('class_section_id', 'subject_id', 'teacher_id')
    def _check_university_links(self):
        for channel in self:
            section = channel.class_section_id

            # 1. Subject consistency between channel and section
            if section and channel.subject_id and section.subject_id:
                if channel.subject_id != section.subject_id:
                    raise ValidationError(_(
                        "The course subject '%(course_subj)s' must match the class section subject '%(sec_subj)s'.",
                        course_subj=channel.subject_id.name,
                        sec_subj=section.subject_id.name,
                    ))

            # 2. Teacher subject qualification constraint (checked independently of section presence)
            if channel.teacher_id and channel.subject_id:
                if channel.teacher_id.subject_ids and channel.subject_id not in channel.teacher_id.subject_ids:
                    raise ValidationError(_(
                        "Teacher '%(teacher)s' is not assigned to subject '%(subject)s'.",
                        teacher=channel.teacher_id.name,
                        subject=channel.subject_id.name,
                    ))

            # 3. Teacher consistency between channel and section
            if section and channel.teacher_id and section.teacher_id:
                if channel.teacher_id != section.teacher_id:
                    raise ValidationError(_(
                        "Teacher '%(teacher)s' does not match the designated section teacher '%(sec_teacher)s'.",
                        teacher=channel.teacher_id.name,
                        sec_teacher=section.teacher_id.name,
                    ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("class_section_id"):
                section = self.env["university.class.section"].browse(vals["class_section_id"])
                if section.subject_id and "subject_id" not in vals:
                    vals["subject_id"] = section.subject_id.id
                if section.teacher_id and "teacher_id" not in vals:
                    vals["teacher_id"] = section.teacher_id.id
                if section.teacher_id and section.teacher_id.user_id and "user_id" not in vals:
                    vals["user_id"] = section.teacher_id.user_id.id
            elif vals.get("teacher_id"):
                teacher = self.env["university.teacher"].browse(vals["teacher_id"])
                if teacher.user_id and "user_id" not in vals:
                    vals["user_id"] = teacher.user_id.id
                if not vals.get("subject_id") and len(teacher.subject_ids) == 1:
                    vals["subject_id"] = teacher.subject_ids[0].id

        channels = super().create(vals_list)
        channels._sync_section_members()
        return channels

    def write(self, vals):
        if "class_section_id" in vals:
            new_section_id = vals.get("class_section_id")
            if new_section_id:
                section = self.env["university.class.section"].browse(new_section_id)
                if section.subject_id and "subject_id" not in vals:
                    vals["subject_id"] = section.subject_id.id
                if section.teacher_id and "teacher_id" not in vals:
                    vals["teacher_id"] = section.teacher_id.id
                if section.teacher_id and section.teacher_id.user_id and "user_id" not in vals:
                    vals["user_id"] = section.teacher_id.user_id.id

            old_sections_map = {channel.id: channel.class_section_id for channel in self}
            res = super().write(vals)
            for channel in self:
                old_section = old_sections_map.get(channel.id)
                if old_section and old_section.id != new_section_id:
                    channel._remove_section_members(old_section)
                if new_section_id:
                    channel._sync_section_members()
            return res
        return super().write(vals)

    def _sync_section_members(self):
        """Auto-enroll all actively enrolled students of the linked class section as channel members."""
        for channel in self:
            if not channel.class_section_id:
                continue
            enrollments = self.env["university.enrollment"].search([
                ("class_section_id", "=", channel.class_section_id.id),
                ("status", "=", "enrolled"),
            ])
            for enrollment in enrollments:
                user = enrollment.student_id.user_id
                partner = user.partner_id if user else False
                if partner:
                    channel.sudo()._action_add_members(partner)

    def _remove_section_members(self, section):
        """Remove membership for students of an unlinked section, unless they remain enrolled via another section."""
        if not section:
            return
        enrollments = self.env["university.enrollment"].search([
            ("class_section_id", "=", section.id),
            ("status", "=", "enrolled"),
        ])
        for channel in self:
            for enrollment in enrollments:
                user = enrollment.student_id.user_id
                partner = user.partner_id if user else False
                if not partner:
                    continue
                # Keep membership if student is actively enrolled in another section sharing this channel
                other_active = self.env["university.enrollment"].search([
                    ("id", "!=", enrollment.id),
                    ("student_id", "=", enrollment.student_id.id),
                    ("status", "=", "enrolled"),
                    ("class_section_id.slide_channel_ids", "in", channel.ids),
                ], limit=1)
                if not other_active:
                    existing = self.env["slide.channel.partner"].sudo().search([
                        ("channel_id", "=", channel.id),
                        ("partner_id", "=", partner.id),
                    ])
                    if existing:
                        channel.sudo()._remove_membership(partner.ids)

    def action_view_class_section(self):
        self.ensure_one()
        if not self.class_section_id:
            return False
        return {
            "name": _("Class Section - %s", self.class_section_id.name),
            "type": "ir.actions.act_window",
            "res_model": "university.class.section",
            "res_id": self.class_section_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_sync_section_members(self):
        self.ensure_one()
        self._sync_section_members()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("eLearning Member Sync"),
                "message": _("Students enrolled in section '%(section)s' have been synchronized to this course.",
                             section=self.class_section_id.name if self.class_section_id else _("None")),
                "type": "success",
                "sticky": False,
            },
        }

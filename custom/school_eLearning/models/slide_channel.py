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
        help="Specific class section enrolled in this course channel.",
    )

    @api.onchange('class_section_id')
    def _onchange_class_section_id(self):
        # Filling values belongs here, not in a constraint.
        section = self.class_section_id
        if section:
            self.subject_id = section.subject_id
            if not self.teacher_id:
                self.teacher_id = section.teacher_id

    @api.constrains('class_section_id', 'subject_id', 'teacher_id')
    def _check_university_links(self):
        for channel in self:
            section = channel.class_section_id
            if not section:
                continue
            if channel.subject_id and section.subject_id \
                    and channel.subject_id != section.subject_id:
                raise ValidationError(_(
                    "The course subject must match the class section subject."))
            # teacher has subject_ids (many), so use "in", not "=="
            if channel.teacher_id and channel.subject_id \
                    and channel.subject_id not in channel.teacher_id.subject_ids:
                raise ValidationError(_(
                    "This teacher is not assigned to this subject."))
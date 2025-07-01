# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventTagCategory(models.Model):
    _inherit = 'event.tag.category'

    hr_resume_line_type_id = fields.Many2one(
        'hr.resume.line.type', "Resume Section", ondelete='set null',
        help="Assigning a Resume Section will automatically create a resume entry for employees who attend the event.",
    )

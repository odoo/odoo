# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import html2plaintext


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    def _recompute_completion(self):
        res = super(SlideChannelPartner, self)._recompute_completion()
        partner_has_completed = {channel_partner.partner_id.id: channel_partner.channel_id for channel_partner in self.filtered('completed')}
        employees = self.env['hr.employee'].sudo().search([('user_id.partner_id', 'in', list(partner_has_completed.keys()))])
        if not employees:
            return res
        line_type = self.env.ref('hr_skills_slides.resume_type_training', raise_if_not_found=False)
        resume_line_vals = []
        for employee in employees:
            # If an employee has completed a course once, and new content is added afterwards, course is still considered
            # as completed for an employee, so do not add duplicate skill(resume line) for the same course
            channel = partner_has_completed[employee.user_id.partner_id.id]
            if employee.resume_line_ids.filtered(lambda skill: skill.display_type == 'course' and skill.channel_id == channel):
                continue
            resume_line_vals.append({
                'employee_id': employee.id,
                'name': channel.name,
                'date_start': fields.Date.today(),
                'date_end': fields.Date.today(),
                'description': html2plaintext(channel.description),
                'line_type_id': line_type and line_type.id,
                'display_type': 'course',
                'channel_id': channel.id
            })
        if resume_line_vals:
            self.env['hr.resume.line'].create(resume_line_vals)
        return res

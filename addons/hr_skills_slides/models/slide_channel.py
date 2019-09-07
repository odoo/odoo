# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ChannelUsersRelation(models.Model):
    _inherit = 'slide.channel.partner'

    def _post_completion_hook(self):
        partner_has_completed = {channel_partner.partner_id.id: channel_partner.channel_id for channel_partner in self}
        employees = self.env['hr.employee'].sudo().search([('user_id.partner_id', 'in', list(partner_has_completed.keys()))])
        for employee in employees:
            line_type = self.env.ref('hr_skills_slides.resume_type_training', raise_if_not_found=False)
            channel = partner_has_completed[employee.user_id.partner_id.id]
            self.env['hr.resume.line'].create({
                'employee_id': employee.id,
                'name': channel.name,
                'date_start': fields.Date.today(),
                'date_end': fields.Date.today(),
                'description': channel.description,
                'line_type_id': line_type and line_type.id,
                'display_type': 'course',
                'channel_id': channel.id
            })
        return super()._post_completion_hook()


class ResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    display_type = fields.Selection(selection_add=[('course', 'Course')])
    channel_id = fields.Many2one('slide.channel', string="Course", readonly=True)

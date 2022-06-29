# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import html2plaintext


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    def _recompute_completion(self):
        res = super(SlideChannelPartner, self)._recompute_completion()
        partner_has_completed = {
            channel_partner.partner_id.id: channel_partner.channel_id for channel_partner in self
            if channel_partner.completed}
        employees = self.env['hr.employee'].sudo().search(
            [('user_id.partner_id', 'in', list(partner_has_completed.keys()))])

        if employees:
            HrResumeLine = self.env['hr.resume.line'].sudo()
            line_type = self.env.ref('hr_skills_slides.resume_type_training', raise_if_not_found=False)
            line_type_id = line_type and line_type.id

            for employee in employees:
                channel = partner_has_completed[employee.user_id.partner_id.id]

                already_added = HrResumeLine.search([
                    ("employee_id", "in", employees.ids),
                    ("channel_id", "=", channel.id),
                    ("line_type_id", "=", line_type_id),
                    ("display_type", "=", "course")
                ])

                if not already_added:
                    HrResumeLine.create({
                        'employee_id': employee.id,
                        'name': channel.name,
                        'date_start': fields.Date.today(),
                        'date_end': fields.Date.today(),
                        'description': html2plaintext(channel.description),
                        'line_type_id': line_type_id,
                        'display_type': 'course',
                        'channel_id': channel.id
                    })
        return res

    def _send_completed_mail(self):
        super()._send_completed_mail()
        for scp in self:
            if self.env.user.employee_ids:
                msg = _('The employee has completed the course <a href="%(link)s">%(course)s</a>',
                    link=scp.channel_id.website_url,
                    course=scp.channel_id.name)
                self.env.user.employee_id.message_post(body=msg)

class Channel(models.Model):
    _inherit = 'slide.channel'

    def _action_add_members(self, target_partners, **member_values):
        res = super()._action_add_members(target_partners, **member_values)

        if self.env.user.employee_ids:
            msg = _('The employee subscribed to the course <a href="%(link)s">%(course)s</a>',
                link=self.website_url,
                course=self.name)
            self.env.user.employee_id.message_post(body=msg)

        return res

    def _remove_membership(self, partner_ids):
        res = super()._remove_membership(partner_ids)

        if self.env.user.employee_ids:
            msg = _('The employee left the course <a href="%(link)s">%(course)s</a>',
                link=self.website_url,
                course=self.name)
            self.env.user.employee_id.message_post(body=msg)

        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'

    def _recompute_completion(self):
        res = super(SlideChannelPartner, self)._recompute_completion()
        partner_has_completed = {
            channel_partner.partner_id.id: channel_partner.channel_id for channel_partner in self
            if channel_partner.member_status == 'completed'}
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
        for channel in self.channel_id:
            partners = self.filtered(lambda scp: scp.channel_id == channel).partner_id
            channel._message_employee_chatter('completed', partners)


class Channel(models.Model):
    _inherit = 'slide.channel'

    def _action_add_members(self, target_partners, member_status='joined', raise_on_access=False):
        res = super()._action_add_members(target_partners, member_status=member_status, raise_on_access=raise_on_access)
        if member_status == 'joined':
            self._message_employee_chatter(member_status, target_partners)
        return res

    def _remove_membership(self, partner_ids):
        res = super()._remove_membership(partner_ids)
        partners = self.env['res.partner'].browse(partner_ids)
        self._message_employee_chatter('left', partners)
        return res

    def _message_employee_chatter(self, kind, partners):
        """Post a notification about the changes in member_status of employees in the course(s).

        :param str kind: "joined", "left", "completed"
        :param partners: res.partner recordset
        """
        if not partners or not self.ids or kind not in {"joined", "left", "completed"}:
            return

        if not self.env.ref('hr_skills_slides.message_employee_course_status_changed', raise_if_not_found=False):
            _logger.warning('Missing template `hr_skills_slides.message_employee_course_status_changed`')
            return

        employees_sudo = partners.sudo().mapped(
            lambda p: p.user_ids.employee_id.filtered(lambda e: not e.company_id or e.company_id == p.company_id))

        if not employees_sudo:
            return

        for channel in self:
            employees_sudo.message_post_with_source(
                'hr_skills_slides.message_employee_course_status_changed',
                render_values={'channel_name': channel.name, 'channel_website_url': channel.website_url, 'kind': kind},
            )

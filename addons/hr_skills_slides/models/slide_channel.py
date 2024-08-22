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
        completed_membership = self.filtered(lambda m: m.member_status == 'completed')
        if not completed_membership:
            return res
        partner_has_completed = {
            membership.partner_id.id: membership.channel_id
            for membership in completed_membership
        }
        employees = self.env['hr.employee'].sudo().search(
            [('user_id.partner_id', 'in', completed_membership.partner_id.ids)])

        if employees:
            HrResumeLine = self.env['hr.resume.line'].sudo()
            line_type = self.env.ref('hr_skills_slides.resume_type_training', raise_if_not_found=False)
            line_type_id = line_type and line_type.id

            lines_for_channel_by_employee = dict(HrResumeLine._read_group([
                ('employee_id', 'in', employees.ids),
                ('channel_id', 'in', completed_membership.channel_id.ids),
                ('line_type_id', '=', line_type_id),
                ('display_type', '=', 'course')
            ], ['employee_id'], ['channel_id:array_agg']))

            lines_to_create = []
            for employee in employees:
                channel = partner_has_completed[employee.user_id.partner_id.id]

                if channel.id not in lines_for_channel_by_employee.get(employee, []):
                    lines_to_create.append({
                        'employee_id': employee.id,
                        'name': channel.name,
                        'date_start': fields.Date.today(),
                        'date_end': fields.Date.today(),
                        'description': html2plaintext(channel.description),
                        'line_type_id': line_type_id,
                        'display_type': 'course',
                        'channel_id': channel.id
                    })
            if lines_to_create:
                HrResumeLine.create(lines_to_create)
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

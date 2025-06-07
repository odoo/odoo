# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, models, _
from odoo.tools import html2plaintext


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
        for scp in self:
            if self.env.user.employee_ids:
                msg = _('The employee has completed the course %s',
                    Markup('<a href="%(link)s">%(course)s</a>') % {
                        'link': scp.channel_id.website_url,
                        'course': scp.channel_id.name,
                })
                self.env.user.employee_id.message_post(body=msg)

class Channel(models.Model):
    _inherit = 'slide.channel'

    def _action_add_members(self, target_partners, member_status='joined', raise_on_access=False):
        res = super()._action_add_members(target_partners, member_status=member_status, raise_on_access=raise_on_access)
        if member_status == 'joined':
            for channel in self:
                channel._message_employee_chatter(
                    _('The employee subscribed to the course %s',
                        Markup('<a href="%(link)s">%(course)s</a>') % {
                            'link': channel.website_url,
                            'course': channel.name
                    }),
                    target_partners
                )
        return res

    def _remove_membership(self, partner_ids):
        res = super()._remove_membership(partner_ids)

        partners = self.env['res.partner'].browse(partner_ids)

        for channel in self:
            channel._message_employee_chatter(
                _('The employee left the course %s',
                    Markup('<a href="%(link)s">%(course)s</a>') % {
                        'link': channel.website_url,
                        'course': channel.name,
                }),
                partners)
        return res

    def _message_employee_chatter(self, msg, partners):
        for partner in partners:
            employee = partner.user_ids.sudo().filtered(
                lambda u: u.employee_id and (not partner.company_id or u.employee_id.company_id == partner.company_id)
            ).employee_id

            if employee:
                employee.sudo().message_post(body=msg)

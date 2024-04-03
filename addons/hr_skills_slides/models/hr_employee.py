# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Employee(models.Model):
    _inherit = 'hr.employee'

    subscribed_courses = fields.Many2many('slide.channel', related='user_partner_id.slide_channel_ids')
    courses_completion_text = fields.Char(compute="_compute_courses_completion_text")

    @api.depends_context('lang')
    def _compute_courses_completion_text(self):
        for employee in self:
            if not employee.user_partner_id:
                employee.courses_completion_text = False
                continue
            total_completed_courses = len(employee.user_partner_id.slide_channel_completed_ids)
            employee.courses_completion_text = _("%(completed)s / %(total)s",
                completed=total_completed_courses,
                total=len(employee.subscribed_courses))

    def action_open_courses(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/profile/user/%s' % self.user_id.id,
        }

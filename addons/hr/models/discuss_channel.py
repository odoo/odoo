# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    subscription_department_ids = fields.Many2many(
        'hr.department', string='HR Departments',
        help='Automatically subscribe members of those departments to the channel.')

    @api.constrains('subscription_department_ids')
    def _constraint_subscription_department_ids_channel(self):
        failing_channels = self.sudo().filtered(lambda channel: channel.channel_type != 'channel' and channel.subscription_department_ids)
        if failing_channels:
            raise ValidationError(_("For %(channels)s, channel_type should be 'channel' to have the department auto-subscription.", channels=', '.join([ch.name for ch in failing_channels])))

    def _get_auto_subscribe_domain(self):
        domain = super()._get_auto_subscribe_domain()
        # sudo - hr.department: ensure all departments and its members are accesible
        sudo_departments = self.sudo().subscription_department_ids
        if sudo_departments:
            department_domain = Domain(
                'id', 'in', sudo_departments.member_ids.user_id.ids,
            )
            if self.group_ids:
                domain &= Domain('all_group_ids', 'in', self.group_ids.ids) | department_domain
            else:
                domain &= department_domain
        return domain

    def write(self, vals):
        res = super().write(vals)
        if vals.get('subscription_department_ids'):
            self._subscribe_users_automatically()
        return res

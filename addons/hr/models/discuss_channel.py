# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    subscription_department_ids = fields.Many2many(
        'hr.department', string='HR Departments',
        help="Restrict auto-subscribe users based on their related employees' departments.")

    @api.constrains('subscription_department_ids')
    def _constraint_subscription_department_ids_channel(self):
        failing_channels = self.sudo().filtered(lambda channel: channel.channel_type != 'channel' and channel.subscription_department_ids)
        if failing_channels:
            raise ValidationError(_("For %(channels)s, channel_type should be 'channel' to have the department auto-subscription.", channels=', '.join([ch.name for ch in failing_channels])))

    def _get_extra_domain(self):
        domain = super()._get_extra_domain()
        # sudo: hr.department - ensure all departments and their members are accessible
        departments_sudo = self.sudo().subscription_department_ids
        if departments_sudo:
            department_domain = Domain(
                'id', 'in', departments_sudo.member_ids.user_id.ids,
            )
            if self.group_ids:
                domain |= department_domain
            else:
                domain &= department_domain
        return domain

    def write(self, vals):
        res = super().write(vals)
        if vals.get('subscription_department_ids'):
            self._subscribe_users_automatically()
        return res

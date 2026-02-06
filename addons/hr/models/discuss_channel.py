# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Channel(models.Model):
    _inherit = 'discuss.channel'

    subscription_department_ids = fields.Many2many(
        'hr.department', string='HR Departments',
        help='Automatically subscribe members of those departments to the channel.')

    @api.constrains('subscription_department_ids')
    def _constraint_subscription_department_ids_channel(self):
        failing_channels = self.sudo().filtered(lambda channel: channel.channel_type != 'channel' and channel.subscription_department_ids)
        if failing_channels:
            raise ValidationError(_("For %(channels)s, channel_type should be 'channel' to have the department auto-subscription.", channels=', '.join([ch.name for ch in failing_channels])))

    def _subscribe_users_automatically_get_members(self):
        """ Auto-subscribe members of a department to a channel """
        new_members = super(Channel, self)._subscribe_users_automatically_get_members()
        for channel in self:

            partners_to_add = self.env["hr.employee"].search_fetch([
                ('user_id.partner_id', 'not in', channel.channel_partner_ids.ids),
                ('department_id', 'child_of', channel.subscription_department_ids.ids),
                ('user_id.partner_id.active', '=', True)
            ], field_names=['user_id']).user_id.partner_id
            new_members[channel.id] = list(set(new_members[channel.id]) | set(partners_to_add.ids))
        return new_members

    def write(self, vals):
        res = super(Channel, self).write(vals)
        if vals.get('subscription_department_ids'):
            self._subscribe_users_automatically()
        return res

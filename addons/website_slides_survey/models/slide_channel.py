# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.osv import expression

class ChannelUsersRelation(models.Model):
    _inherit = 'slide.channel.partner'

    nbr_certification = fields.Integer(related='channel_id.nbr_certification')
    survey_certification_success = fields.Boolean('Certified')

class Channel(models.Model):
    _inherit = 'slide.channel'

    members_certified_count = fields.Integer('# Certified Attendees', compute='_compute_members_certified_count')
    nbr_certification = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)

    def _remove_membership(self, partner_ids):
        """Remove the relationship between the user_input and the slide_partner_id.

        Removing the relationship between the user_input from the slide_partner_id allows to keep
        track of the current pool of attempts allowed since the user (last) joined
        the course, as only those will have a slide_partner_id."""
        if self:
            removed_channel_partner_domain = expression.OR([
                [('partner_id', 'in', partner_ids), ('channel_id', '=', channel.id)]
                for channel in self
            ])
            slide_partners_sudo = self.env['slide.slide.partner'].sudo().search(
                removed_channel_partner_domain)
            slide_partners_sudo.user_input_ids.slide_partner_id = False
        return super()._remove_membership(partner_ids)

    @api.depends('channel_partner_ids')
    def _compute_members_certified_count(self):
        channels_count = self.env['slide.channel.partner'].sudo()._read_group(
            domain=[('channel_id', 'in', self.ids),
                    ('survey_certification_success', '=', True)],
            groupby=['channel_id'],
            aggregates=['__count']
        )
        mapped_data = dict(channels_count)
        for channel in self:
            channel.members_certified_count = mapped_data.get(channel, 0)

    def action_redirect_to_certified_members(self):
        action = self.action_redirect_to_members('certified')
        msg = _('No Attendee passed this course certification yet!')
        action['help'] = Markup('<p class="o_view_nocontent_smiling_face">%s</p>') % msg
        return action

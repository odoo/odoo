# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class Channel(models.Model):
    _inherit = 'slide.channel'

    nbr_certification = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)

    def _remove_membership(self, partner_ids):
        """Remove the relationship between the user_input and the slide_partner_id.

        Removing the relationship between the user_input from the slide_partner_id allows to keep
        track of the current pool of attempts allowed since the user (last) joined
        the course, as only those will have a slide_partner_id."""
        removed_channel_partner_domain = []
        for channel in self:
            removed_channel_partner_domain = expression.OR([
                removed_channel_partner_domain,
                [('partner_id', 'in', partner_ids), ('channel_id', '=', channel.id)]
            ])
        if removed_channel_partner_domain:
            slide_partners_sudo = self.env['slide.slide.partner'].sudo().search(
                removed_channel_partner_domain)
            slide_partners_sudo.user_input_ids.slide_partner_id = False
        return super()._remove_membership(partner_ids)

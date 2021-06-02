# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def create(self, vals):
        """ Automatically subscribe employee users to default digest if activated """
        user = super(ResUsers, self).create(vals)
        default_digest_emails = self.env['ir.config_parameter'].sudo().get_param('digest.default_digest_emails')
        default_digest_id = self.env['ir.config_parameter'].sudo().get_param('digest.default_digest_id')
        if user.has_group('base.group_user') and default_digest_emails and default_digest_id:
            digest = self.env['digest.digest'].sudo().browse(int(default_digest_id))
            digest.user_ids |= user
        return user

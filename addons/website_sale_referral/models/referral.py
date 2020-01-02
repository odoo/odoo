# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ReferralTracking(models.Model):
    _name = 'referral.tracking'
    _description = 'Referral Collection'

    token = fields.Char(required=True, readonly=False, unique=True, index=True, copy=False)
    utm_source_id = fields.Many2one('utm.source', 'Source', ondelete='cascade', groups="base.group_user")
    referrer_email = fields.Char()
    updates_count = fields.Integer(string='Referral Updates')

    _sql_constraints = [
        ('referral_tracking_token_unique', 'unique(token)', 'Referral tracking with this token already exists !'),
        ('referral_tracking_referrer_unique', 'unique(utm_source_id)', 'Referral tracking for this source already exists !')
    ]

    def get_tracking_link(self):
        self.ensure_one()
        tracking_url_relative = '/referral/%s' % (self.token)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return base_url + tracking_url_relative

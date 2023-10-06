# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import secrets
from datetime import datetime, timedelta

from odoo import api, fields, models


class SocialShareUrl(models.Model):
    _name = 'social.share.url'
    _description = 'Social Share URL resolver'

    campaign_id = fields.Many2one('social.share.post')
    shared = fields.Boolean('Shared on Social Networks')
    target_id = fields.Integer()
    uuid = fields.Char(
        'Unique mapping to post url', default=lambda self: secrets.token_urlsafe(),
        readonly=True, required=True
    )
    message = fields.Char('Thank-You message')

    _sql_constraints = [
        ('campaign_target_unique', 'unique(campaign_id, target_id)',
         'Each target should be unique for a campaign'),
        ('campaign_uuid_unique', 'unique(campaign_id, uuid)',
         'Each uuid should be unique for a campaign'),
    ]

    @api.autovacuum
    def _gc_social_share_urls(self):
        """Remove innactive records after a month."""
        # TODO based on campaign status?
        self.search([('write_date', '<=', datetime.now() - timedelta(days=30))]).unlink()

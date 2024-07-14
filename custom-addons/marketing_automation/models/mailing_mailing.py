# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MassMailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.model
    def default_get(self, fields):
        vals = super(MassMailing, self).default_get(fields)
        if 'subject' in fields and self.env.context.get('default_use_in_marketing_automation', False):
            vals['subject'] = self.env.context.get('default_name')
        return vals

    use_in_marketing_automation = fields.Boolean(
        string='Specific mailing used in marketing campaign', default=False,
        help='Marketing campaigns use mass mailings with some specific behavior; this field is used to indicate its statistics may be suspicious.')
    marketing_activity_ids = fields.One2many('marketing.activity', 'mass_mailing_id', string='Marketing Activities', copy=False)

    # TODO: remove in master
    def convert_links(self):
        """Override convert_links so we can add marketing automation campaign instead of mass mail campaign"""
        res = {}
        done = self.env['mailing.mailing']
        for mass_mailing in self:
            if self.env.context.get('default_marketing_activity_id'):
                activity = self.env['marketing.activity'].browse(self.env.context['default_marketing_activity_id'])
                vals = {
                    'mass_mailing_id': mass_mailing.id,
                    'campaign_id': activity.campaign_id.utm_campaign_id.id,
                    'source_id': activity.source_id.id,
                    'medium_id': mass_mailing.medium_id.id,
                }
                res[mass_mailing.id] = mass_mailing._shorten_links(
                    mass_mailing.body_html or '',
                    vals,
                    blacklist=['/unsubscribe_from_list', '/view']
                )
                done |= mass_mailing
        res.update(super(MassMailing, self - done).convert_links())
        return res

    def _get_link_tracker_values(self):
        # We don't want to create link trackers for tests
        if self.env.context.get('active_model') == 'marketing.campaign.test':
            return {}
        res = super(MassMailing, self)._get_link_tracker_values()
        if self.env.context.get('default_marketing_activity_id'):
            activity = self.env['marketing.activity'].browse(self.env.context['default_marketing_activity_id'])
            res['campaign_id'] = activity.campaign_id.utm_campaign_id.id
            res['source_id'] = activity.source_id.id
        return res

    def _get_seen_list_extra(self):
        return ('LEFT JOIN marketing_trace m ON (s.marketing_trace_id = m.id)', 'AND (m.is_test IS NULL OR m.is_test = false)')

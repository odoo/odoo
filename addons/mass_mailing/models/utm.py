# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    mailing_mail_ids = fields.One2many(
        'mailing.mailing', 'campaign_id',
        domain=[('mailing_type', '=', 'mail')],
        string='Mass Mailings')
    mailing_mail_count = fields.Integer('Number of Mass Mailing', compute="_compute_mailing_mail_count")

    # A/B Testing
    ab_testing_mailings_count = fields.Integer("A/B Test Mailings #", compute="_compute_mailing_mail_count")
    ab_testing_completed = fields.Boolean("A/B Testing Campaign Finished")
    ab_testing_schedule_datetime = fields.Datetime('Send Final On',
        default=lambda self: fields.Datetime.now() + relativedelta(days=1),
        help="Date that will be used to know when to determine and send the winner mailing")
    ab_testing_total_pc = fields.Integer("Total A/B test percentage", compute="_compute_ab_testing_total_pc", store=True)
    ab_testing_winner_selection = fields.Selection([
        ('manual', 'Manual'),
        ('opened_ratio', 'Highest Open Rate'),
        ('clicks_ratio', 'Highest Click Rate'),
        ('replied_ratio', 'Highest Reply Rate')], string="Winner Selection", default="opened_ratio",
        help="Selection to determine the winner mailing that will be sent.")

    # stat fields
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", string='Bounced Ratio')

    @api.depends('mailing_mail_ids')
    def _compute_ab_testing_total_pc(self):
        for campaign in self:
            campaign.ab_testing_total_pc = sum([
                mailing.ab_testing_pc for mailing in campaign.mailing_mail_ids.filtered('ab_testing_enabled')
            ])

    @api.depends('mailing_mail_ids')
    def _compute_mailing_mail_count(self):
        if self.ids:
            mailing_data = self.env['mailing.mailing'].read_group(
                [('campaign_id', 'in', self.ids), ('mailing_type', '=', 'mail')],
                ['campaign_id', 'ab_testing_enabled'],
                ['campaign_id', 'ab_testing_enabled'],
                lazy=False,
            )
            ab_testing_mapped_data = {}
            mapped_data = {}
            for data in mailing_data:
                if data['ab_testing_enabled']:
                    ab_testing_mapped_data.setdefault(data['campaign_id'][0], []).append(data['__count'])
                mapped_data.setdefault(data['campaign_id'][0], []).append(data['__count'])
        else:
            mapped_data = dict()
            ab_testing_mapped_data = dict()
        for campaign in self:
            campaign.mailing_mail_count = sum(mapped_data.get(campaign.id, []))
            campaign.ab_testing_mailings_count = sum(ab_testing_mapped_data.get(campaign.id, []))

    @api.constrains('ab_testing_total_pc', 'ab_testing_completed')
    def _check_ab_testing_total_pc(self):
        for campaign in self:
            if not campaign.ab_testing_completed and campaign.ab_testing_total_pc >= 100:
                raise ValidationError(_("The total percentage for an A/B testing campaign should be less than 100%"))

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing campaign """
        default_vals = {
            'received_ratio': 0,
            'opened_ratio': 0,
            'replied_ratio': 0,
            'bounced_ratio': 0
        }
        if not self.ids:
            self.update(default_vals)
            return
        self.env.cr.execute("""
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS expected,
                COUNT(s.sent_datetime) AS sent,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('sent', 'open', 'reply')) AS delivered,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('open', 'reply')) AS open,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'reply') AS reply,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'bounce') AS bounce,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'cancel') AS cancel
            FROM
                mailing_trace s
            RIGHT JOIN
                utm_campaign c
                ON (c.id = s.campaign_id)
            WHERE
                c.id IN %s
            GROUP BY
                c.id
        """, (tuple(self.ids), ))

        all_stats = self.env.cr.dictfetchall()
        stats_per_campaign = {
            stats['campaign_id']: stats
            for stats in all_stats
        }

        for campaign in self:
            stats = stats_per_campaign.get(campaign.id)
            if not stats:
                vals = default_vals
            else:
                total = (stats['expected'] - stats['cancel']) or 1
                delivered = stats['sent'] - stats['bounce']
                vals = {
                    'received_ratio': 100.0 * delivered / total,
                    'opened_ratio': 100.0 * stats['open'] / total,
                    'replied_ratio': 100.0 * stats['reply'] / total,
                    'bounced_ratio': 100.0 * stats['bounce'] / total
                }

            campaign.update(vals)

    def _get_mailing_recipients(self, model=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
        build for each mailing. """
        res = dict.fromkeys(self.ids, {})
        for campaign in self:
            domain = [('campaign_id', '=', campaign.id)]
            if model:
                domain += [('model', '=', model)]
            res[campaign.id] = set(self.env['mailing.trace'].search(domain).mapped('res_id'))
        return res

    @api.model
    def _cron_process_mass_mailing_ab_testing(self):
        """ Cron that manages A/B testing and sends a winner mailing computed based on
        the value set on the A/B testing campaign.
        In case there is no mailing sent for an A/B testing campaign we ignore this campaign
        """
        ab_testing_campaign = self.search([
            ('ab_testing_schedule_datetime', '<=', fields.Datetime.now()),
            ('ab_testing_winner_selection', '!=', 'manual'),
            ('ab_testing_completed', '=', False),
        ])
        for campaign in ab_testing_campaign:
            ab_testing_mailings = campaign.mailing_mail_ids.filtered(lambda m: m.ab_testing_enabled)
            if not ab_testing_mailings.filtered(lambda m: m.state == 'done'):
                continue
            ab_testing_mailings.action_send_winner_mailing()
        return ab_testing_campaign

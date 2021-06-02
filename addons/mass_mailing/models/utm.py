# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    mailing_mail_ids = fields.One2many(
        'mailing.mailing', 'campaign_id',
        domain=[('mailing_type', '=', 'mail')],
        string='Mass Mailings')
    mailing_mail_count = fields.Integer('Number of Mass Mailing', compute="_compute_mailing_mail_count")
    mailing_clicks_ratio = fields.Integer(compute="_compute_mailing_clicks_ratio", string="Number of clicks")
    mailing_items = fields.Integer(compute="_compute_mailing_items", string='Mailings')
    mailing_clicked = fields.Integer(compute="_compute_mailing_items", string='Mailings Clicked')
    # stat fields
    total = fields.Integer(compute="_compute_statistics")
    scheduled = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
    ignored = fields.Integer(compute="_compute_statistics")
    sent = fields.Integer(compute="_compute_statistics", string="Sent Emails")
    delivered = fields.Integer(compute="_compute_statistics")
    opened = fields.Integer(compute="_compute_statistics")
    replied = fields.Integer(compute="_compute_statistics")
    bounced = fields.Integer(compute="_compute_statistics")
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", string='Bounced Ratio')

    @api.depends('mailing_mail_ids')
    def _compute_mailing_mail_count(self):
        for campaign in self:
            campaign.mailing_mail_count = len(campaign.mailing_mail_ids)

    def _compute_mailing_items(self):
        query = """SELECT trace.campaign_id AS campaign_id, COUNT(DISTINCT(trace.id)) AS items_total, COUNT(DISTINCT(click.mailing_trace_id)) AS clicked_total
                    FROM mailing_trace AS trace
                    LEFT OUTER JOIN link_tracker_click as click ON click.mailing_trace_id = trace.id
                    WHERE trace.campaign_id IN %s
                    GROUP BY trace.campaign_id """
        params = [tuple(self.ids)]
        self.env.cr.execute(query, params)
        clicked_data = self.env.cr.dictfetchall()
        mapped_data = {datum['campaign_id']: {'clicked_total': datum['clicked_total'], 'items_total': datum['items_total']} for datum in clicked_data}

        for campaign in self:
            campaign_items_values = mapped_data.get(campaign.id, {})
            campaign.mailing_items = campaign_items_values.get('items_total', 0)
            campaign.mailing_clicked = campaign_items_values.get('clicked_total', 0)

    @api.depends('mailing_items', 'mailing_clicked')
    def _compute_mailing_clicks_ratio(self):
        for campaign in self:
            campaign.mailing_clicks_ratio = campaign.mailing_clicked / campaign.mailing_items * 100 if campaign.mailing_items > 0 else 0

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing campaign """
        self.env.cr.execute("""
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS total,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is not null THEN 1 ELSE null END) AS ignored,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied ,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
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

        for row in self.env.cr.dictfetchall():
            total = (row['total'] - row['ignored']) or 1
            row['delivered'] = row['sent'] - row['bounced']
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('campaign_id')).update(row)

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

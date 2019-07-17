# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class MailingTraceReport(models.Model):
    _name = 'mailing.trace.report'
    _auto = False
    _description = 'Mass Mailing Statistics'

    scheduled_date = fields.Datetime(string='Scheduled Date', readonly=True)
    name = fields.Char(string='Mass Mail', readonly=True)
    campaign = fields.Char(string='Mass Mail Campaign', readonly=True)
    sent = fields.Integer(readonly=True)
    delivered = fields.Integer(readonly=True)
    opened = fields.Integer(readonly=True)
    bounced = fields.Integer(readonly=True)
    replied = fields.Integer(readonly=True)
    clicked = fields.Integer(readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')],
        string='Status', readonly=True)
    email_from = fields.Char('From', readonly=True)

    def init(self):
        """Mass Mail Statistical Report: based on mailing.trace that models the various
        statistics collected for each mailing, and mailing.mailing model that models the
        various mailing performed. """
        tools.drop_view_if_exists(self.env.cr, 'mailing_trace_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW mailing_trace_report AS (
                SELECT
                    min(ms.id) as id,
                    ms.scheduled as scheduled_date,
                    utm_source.name as name,
                    utm_campaign.name as campaign,
                    count(ms.bounced) as bounced,
                    count(ms.sent) as sent,
                    (count(ms.sent) - count(ms.bounced)) as delivered,
                    count(ms.opened) as opened,
                    count(ms.replied) as replied,
                    count(ms.clicked) as clicked,
                    mm.state,
                    mm.email_from
                FROM
                    mailing_trace as ms
                    left join mailing_mailing as mm ON (ms.mass_mailing_id=mm.id)
                    left join mail_mass_mailing_campaign as mc ON (ms.mass_mailing_campaign_id=mc.id)
                    left join utm_campaign as utm_campaign ON (mc.campaign_id = utm_campaign.id)
                    left join utm_source as utm_source ON (mm.source_id = utm_source.id)
                GROUP BY ms.scheduled, utm_source.name, utm_campaign.name, mm.state, mm.email_from
            )""")

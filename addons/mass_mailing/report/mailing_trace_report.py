# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.tools import SQL


class MailingTraceReport(models.Model):
    _name = 'mailing.trace.report'
    _auto = False
    _description = 'Mass Mailing Statistics'

    # mailing
    name = fields.Char(string='Mass Mail', readonly=True)
    mailing_type = fields.Selection([('mail', 'Mail')], string='Type', default='mail', required=True)
    campaign = fields.Char(string='Mailing Campaign', readonly=True)
    scheduled_date = fields.Datetime(string='Scheduled Date', readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')],
        string='Status', readonly=True)
    email_from = fields.Char('From', readonly=True)
    # traces
    scheduled = fields.Integer(readonly=True)
    processing = fields.Integer(readonly=True)
    pending = fields.Integer(readonly=True)  # Used with SMS before a delivery report is received
    sent = fields.Integer(readonly=True)
    delivered = fields.Integer(readonly=True)
    error = fields.Integer(readonly=True)
    opened = fields.Integer(readonly=True)
    replied = fields.Integer(readonly=True)
    bounced = fields.Integer(readonly=True)
    canceled = fields.Integer(readonly=True)
    clicked = fields.Integer(readonly=True)

    def init(self):
        """Mass Mail Statistical Report: based on mailing.trace that models the various
        statistics collected for each mailing, and mailing.mailing model that models the
        various mailing performed. """
        tools.drop_view_if_exists(self.env.cr, 'mailing_trace_report')
        query = SQL(
            """CREATE OR REPLACE VIEW mailing_trace_report AS (
            SELECT %s
            FROM %s
            WHERE %s
            GROUP BY %s
            )
            """,
            SQL(', ').join(self._report_get_request_select_items()),
            SQL('\n').join(self._report_get_request_from_items()),
            SQL(' AND ').join(self._report_get_request_where_items()) or SQL('TRUE'),
            SQL(', ').join(self._report_get_request_group_by_items()),
        )
        self.env.cr.execute(query)

    def _report_get_request_select_items(self):
        return [
            SQL('min(trace.id) as id'),
            SQL('utm_source.name as name'),
            SQL('mailing.mailing_type'),
            SQL('utm_campaign.name as campaign'),
            SQL('trace.create_date as scheduled_date'),
            SQL('mailing.state'),
            SQL('mailing.email_from'),
            SQL("COUNT(trace.id) as scheduled"),
            SQL("COUNT(trace.sent_datetime) as sent"),
            SQL("(COUNT(trace.id) - COUNT(trace.trace_status) FILTER (WHERE trace.trace_status IN ('outgoing', 'pending', 'process', 'error', 'bounce', 'cancel'))) as delivered"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'process') as processing"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'pending') as pending"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'error') as error"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'bounce') as bounced"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'cancel') as canceled"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'open') as opened"),
            SQL("COUNT(trace.trace_status) FILTER (WHERE trace.trace_status = 'reply') as replied"),
            SQL("COUNT(trace.links_click_datetime) as clicked"),
        ]

    def _report_get_request_from_items(self):
        return [
            SQL('mailing_trace as trace'),
            SQL('LEFT JOIN mailing_mailing as mailing ON (trace.mass_mailing_id=mailing.id)'),
            SQL('LEFT JOIN utm_campaign as utm_campaign ON (mailing.campaign_id = utm_campaign.id)'),
            SQL('LEFT JOIN utm_source as utm_source ON (mailing.source_id = utm_source.id)'),
        ]

    def _report_get_request_where_items(self):
        return []

    def _report_get_request_group_by_items(self):
        return [
            SQL('trace.create_date'),
            SQL('utm_source.name'),
            SQL('utm_campaign.name'),
            SQL('mailing.mailing_type'),
            SQL('mailing.state'),
            SQL('mailing.email_from'),
        ]

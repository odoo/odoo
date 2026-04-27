# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingTrace(models.Model):
    _inherit = 'mailing.trace'

    marketing_trace_id = fields.Many2one(
        'marketing.trace', string='Marketing Trace',
        index=True, ondelete='cascade')

    def set_clicked(self, domain=None):
        traces = super(MailingTrace, self).set_clicked(domain=domain)
        marketing_mail_traces = traces.filtered(lambda trace: trace.marketing_trace_id and trace.marketing_trace_id.activity_type == 'email')
        for marketing_trace in marketing_mail_traces.marketing_trace_id:
            marketing_trace.process_event('mail_click')
        return traces

    def set_opened(self, domain=None):
        traces = super(MailingTrace, self).set_opened(domain=domain)
        marketing_mail_traces = traces.filtered(lambda trace: trace.marketing_trace_id and trace.marketing_trace_id.activity_type == 'email')
        for marketing_trace in marketing_mail_traces.marketing_trace_id:
            marketing_trace.process_event('mail_open')
        return traces

    def set_replied(self, domain=None):
        traces = super(MailingTrace, self).set_replied(domain=domain)
        marketing_mail_traces = traces.filtered(lambda trace: trace.marketing_trace_id and trace.marketing_trace_id.activity_type == 'email')
        for marketing_trace in marketing_mail_traces.marketing_trace_id:
            marketing_trace.process_event('mail_reply')
        return traces

    def set_bounced(self, domain=None, bounce_message=False):
        traces = super(MailingTrace, self).set_bounced(domain=domain, bounce_message=bounce_message)
        marketing_mail_traces = traces.filtered(lambda trace: trace.marketing_trace_id and trace.marketing_trace_id.activity_type == 'email')
        for marketing_trace in marketing_mail_traces.marketing_trace_id:
            marketing_trace.process_event('mail_bounce')
        return traces

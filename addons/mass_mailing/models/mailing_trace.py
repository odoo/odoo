# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class MailingTrace(models.Model):
    """ MailingTrace models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them. """
    _name = 'mailing.trace'
    _description = 'Mailing Statistics'
    _rec_name = 'id'
    _order = 'create_date DESC'

    trace_type = fields.Selection([('mail', 'Mail')], string='Type', default='mail', required=True)
    display_name = fields.Char(compute='_compute_display_name')
    # mail data
    mail_mail_id = fields.Many2one('mail.mail', string='Mail', index=True)
    mail_mail_id_int = fields.Integer(
        string='Mail ID (tech)',
        help='ID of the related mail_mail. This field is an integer field because '
             'the related mail_mail can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index=True,
    )
    email = fields.Char(string="Email", help="Normalized email address")
    message_id = fields.Char(string='Message-ID', help="Technical field for the email Message-ID (RFC 2392)")
    # document
    model = fields.Char(string='Document model')
    res_id = fields.Integer(string='Document ID')
    # campaign data
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', index=True, ondelete='cascade')
    campaign_id = fields.Many2one(
        related='mass_mailing_id.campaign_id',
        string='Campaign',
        store=True, readonly=True, index=True)
    # Status
    sent_datetime = fields.Datetime('Sent Datetime', help='Date when the email has been sent. Used for statistics.')
    trace_status = fields.Selection(selection=[
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('open', 'Opened'),
        ('reply', 'Replied'),
        ('bounce', 'Bounced'),
        ('error', 'Exception'),
        ('cancel', 'Canceled')], string='Status', default='outgoing')
    trace_status_update = fields.Datetime('Last Updated On', help='Date when the status has been udpated. Used for statistics.')
    failure_type = fields.Selection(selection=[
        # generic
        ("error", "Unknown error"),
        # mail
        ("m_mail", "Invalid email address"),
        ("m_smtp", "Connection failed (outgoing mail server problem)"),
        ], string='Failure type')
    # Link tracking
    links_click_ids = fields.One2many('link.tracker.click', 'mailing_trace_id', string='Links click')
    links_click_done = fields.Boolean('Links Clicked', help='If customer clicked on at least one tracked link')

    @api.depends('trace_type', 'mass_mailing_id')
    def _compute_display_name(self):
        for trace in self:
            trace.display_name = '%s: %s (%s)' % (trace.trace_type, trace.mass_mailing_id.name, trace.id)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'mail_mail_id' in values:
                values['mail_mail_id_int'] = values['mail_mail_id']
        return super(MailingTrace, self).create(values_list)

    def _find_traces(self, mail_mail_ids=None, message_ids=None, domain=None):
        base_domain = []
        if mail_mail_ids:
            base_domain = [('mail_mail_id_int', 'in', mail_mail_ids)]
        elif message_ids:
            base_domain = [('message_id', 'in', message_ids)]
        if domain and base_domain:
            base_domain = expression.AND([domain, base_domain])
        return self.search(base_domain)

    def set_sent(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else self._find_traces(mail_mail_ids, message_ids, [('trace_status', '!=', 'open')])
        traces.write({'trace_status': 'sent', 'sent_datetime': fields.Datetime.now(), 'failure_type': False})
        return traces

    def set_opened(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else self._find_traces(mail_mail_ids, message_ids, [('trace_status', '!=', 'open')])
        traces.write({'trace_status': 'open', 'trace_status_update': fields.Datetime.now()})
        return traces

    def set_clicked(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else  self._find_traces(mail_mail_ids, message_ids, [('links_click_done', '=', False)])
        traces.write({'trace_status_update': fields.Datetime.now(), 'links_click_done': True})
        return traces

    def set_replied(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else  self._find_traces(mail_mail_ids, message_ids, [('trace_status', '!=', 'reply')])
        traces.write({'trace_status': 'reply', 'trace_status_update': fields.Datetime.now()})
        return traces

    def set_bounced(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else  self._find_traces(mail_mail_ids, message_ids, [('trace_status', 'not in', ('bounce', 'open'))])
        traces.write({'trace_status': 'bounce', 'trace_status_update': fields.Datetime.now()})
        return traces

    def set_failed(self, mail_mail_ids=None, message_ids=None, failure_type=False):
        traces = self if self else self._find_traces(mail_mail_ids, message_ids)
        traces.write({'trace_status': 'error', 'trace_status_update': fields.Datetime.now(), 'failure_type': failure_type})
        return traces

    def set_canceled(self, mail_mail_ids=None, message_ids=None):
        traces = self if self else self._find_traces(mail_mail_ids, message_ids)
        traces.write({'trace_status': 'cance', 'trace_status_update': fields.Datetime.now()})
        return traces

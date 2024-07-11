# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingTrace(models.Model):
    """ MailingTrace models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them.

    Note:: State management / Error codes / Failure types summary

      * trace_status
        'outgoing', 'process', 'pending', 'sent', 'opened', 'replied',
        'error', 'bounce', 'cancel'
      * failure_type
        # generic
        'unknown',
        # mass_mailing
        "mail_email_invalid", "mail_smtp", "mail_email_missing",
        "mail_from_invalid", "mail_from_missing",
        # mass mailing mass mode specific codes
        "mail_bl", "mail_optout", "mail_dup"
        # mass_mailing_sms
        'sms_number_missing', 'sms_number_format', 'sms_credit', 'sms_server',
        'sms_acc', 'sms_country_not_supported', 'sms_registration_needed',
        # mass_mailing_sms mass mode specific codes
        'sms_blacklist', 'sms_duplicate', 'sms_optout',
      * cancel:
        * mail: set in _prepare_mail_values in composer, if email is blacklisted
          (mail) or in opt_out / seen list (mass_mailing) or email_to is void
          or incorrectly formatted (mass_mailing) - based on mail cancel state
        * sms: set in _prepare_mass_sms_trace_values in composer if sms is
          in cancel state; either blacklisted (sms) or in opt_out / seen list
          (sms);
        * void mail / void sms number -> error (mail_missing, sms_number_missing)
        * invalid mail / invalid sms number -> error (RECIPIENT, sms_number_format)
      * exception: set in  _postprocess_sent_message (_postprocess_iap_sent_sms)
        if mail (sms) not sent with failure type, reset if sent;
      * process: (used in sms): set in SmsTracker._update_sms_traces when held back
        (at IAP) before actual sending to the sms_service.
      * pending: (used in sms): default value for sent sms.
      * sent: set in
        * _postprocess_sent_message if mail
        * SmsTracker._update_sms_traces if sms, when delivery report is received.
      * clicked: triggered by add_click
      * opened: triggered by add_click + blank gif (mail) + gateway reply (mail)
      * replied: triggered by gateway reply (mail)
      * bounced: triggered by gateway bounce (mail) or in _prepare_mass_sms_trace_values
        if sms_number_format error when sending sms (sms)
    """
    _name = 'mailing.trace'
    _description = 'Mailing Statistics'
    _rec_name = 'id'
    _order = 'create_date DESC'

    trace_type = fields.Selection([('mail', 'Email')], string='Type', default='mail', required=True)
    # mail data
    mail_mail_id = fields.Many2one('mail.mail', string='Mail', index='btree_not_null')
    mail_mail_id_int = fields.Integer(
        string='Mail ID (tech)',
        help='ID of the related mail_mail. This field is an integer field because '
             'the related mail_mail can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index='btree_not_null',
    )
    email = fields.Char(string="Email", help="Normalized email address")
    message_id = fields.Char(string='Message-ID') # email Message-ID (RFC 2392)
    medium_id = fields.Many2one(related='mass_mailing_id.medium_id')
    source_id = fields.Many2one(related='mass_mailing_id.source_id')
    # document
    model = fields.Char(string='Document model', required=True)
    res_id = fields.Many2oneReference(string='Document ID', model_field='model')
    # campaign data
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', index=True, ondelete='cascade')
    campaign_id = fields.Many2one(
        related='mass_mailing_id.campaign_id',
        string='Campaign',
        store=True, readonly=True, index='btree_not_null')
    # Status
    sent_datetime = fields.Datetime('Sent On')
    open_datetime = fields.Datetime('Opened On')
    reply_datetime = fields.Datetime('Replied On')
    trace_status = fields.Selection(selection=[
        ('outgoing', 'Outgoing'),
        ('process', 'Processing'),
        ('pending', 'Sent'),
        ('sent', 'Delivered'),
        ('open', 'Opened'),
        ('reply', 'Replied'),
        ('bounce', 'Bounced'),
        ('error', 'Exception'),
        ('cancel', 'Canceled')], string='Status', default='outgoing')
    failure_type = fields.Selection(selection=[
        # generic
        ("unknown", "Unknown error"),
        # mail
        ("mail_bounce", "Bounce"),
        ("mail_email_invalid", "Invalid email address"),
        ("mail_email_missing", "Missing email address"),
        ("mail_from_invalid", "Invalid from address"),
        ("mail_from_missing", "Missing from address"),
        ("mail_smtp", "Connection failed (outgoing mail server problem)"),
        # mass mode
        ("mail_bl", "Blacklisted Address"),
        ("mail_dup", "Duplicated Email"),
        ("mail_optout", "Opted Out"),
    ], string='Failure type')
    failure_reason = fields.Text('Failure reason', copy=False, readonly=True)
    # Link tracking
    links_click_ids = fields.One2many('link.tracker.click', 'mailing_trace_id', string='Links click')
    links_click_datetime = fields.Datetime('Clicked On', help='Stores last click datetime in case of multi clicks.')

    _sql_constraints = [
        # Required on a Many2one reference field is not sufficient as actually
        # writing 0 is considered as a valid value, because this is an integer field.
        # We therefore need a specific constraint check.
        ('check_res_id_is_set',
         'CHECK(res_id IS NOT NULL AND res_id !=0 )',
         'Traces have to be linked to records with a not null res_id.')
    ]

    @api.depends('trace_type', 'mass_mailing_id')
    def _compute_display_name(self):
        for trace in self:
            trace.display_name = f'{trace.trace_type}: {trace.mass_mailing_id.name} ({trace.id})'

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'mail_mail_id' in values:
                values['mail_mail_id_int'] = values['mail_mail_id']
        return super(MailingTrace, self).create(values_list)

    def action_view_contact(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self.model,
            'target': 'current',
            'res_id': self.res_id
        }

    def set_sent(self, domain=None):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({'trace_status': 'sent', 'sent_datetime': fields.Datetime.now(), 'failure_type': False})
        return traces

    def set_opened(self, domain=None):
        """ Reply / Open are a bit shared in various processes: reply implies
        open, click implies open. Let us avoid status override by skipping traces
        that are not already opened or replied. """
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.filtered(lambda t: t.trace_status not in ('open', 'reply')).write({'trace_status': 'open', 'open_datetime': fields.Datetime.now()})
        return traces

    def set_clicked(self, domain=None):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({'links_click_datetime': fields.Datetime.now()})
        return traces

    def set_replied(self, domain=None):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({'trace_status': 'reply', 'reply_datetime': fields.Datetime.now()})
        return traces

    def set_bounced(self, domain=None, bounce_message=False):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({
            'failure_reason': bounce_message,
            'failure_type': 'mail_bounce',
            'trace_status': 'bounce',
        })
        return traces

    def set_failed(self, domain=None, failure_type=False):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({'trace_status': 'error', 'failure_type': failure_type})
        return traces

    def set_canceled(self, domain=None):
        traces = self + (self.search(domain) if domain else self.env['mailing.trace'])
        traces.write({'trace_status': 'cancel'})
        return traces

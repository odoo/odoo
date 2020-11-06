# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingTrace(models.Model):
    """ MailingTrace models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them.

    Note:: State management / Error codes / Failure types summary

      * state
        'outgoing', 'sent', 'opened', 'replied',
        'exception', 'bounced', 'ignored'
      * failure_type
        # mass_mailing
        "SMTP", "RECIPIENT", "BOUNCE", "UNKNOWN"
        # mass_mailing_sms
        'sms_number_missing', 'sms_number_format', 'sms_credit',
        'sms_server', 'sms_acc'
        # mass_mailing_sms mass mode specific codes
        'sms_blacklist', 'sms_duplicate'
      * ignored:
        * mail: set in get_mail_values in composer, if email is blacklisted
          (mail) or in opt_out / seen list (mass_mailing) or email_to is void
          or incorrectly formatted (mass_mailing) - based on mail cancel state
        * sms: set in _prepare_mass_sms_trace_values in composer if sms is
          in cancel state; either blacklisted (sms) or in opt_out / seen list
          (sms);
        * difference: void mail -> cancel -> ignore, void sms -> error
          sms_number_missing -> exception
        * difference: invalid mail -> cancel -> ignore, invalid sms -> error
          sms_number_format -> sent + bounce;
      * exception: set in  _postprocess_sent_message (_postprocess_iap_sent_sms)
        if mail (sms) not sent with failure type, reset if sent; also set for
        sms in _prepare_mass_sms_trace_values if void number
      * sent: set in _postprocess_sent_message (_postprocess_iap_sent_sms) if
        mail (sms) sent
      * clicked: triggered by add_click
      * opened: triggered by add_click + blank gif (mail) + gateway reply (mail)
      * replied: triggered by gateway reply (mail)
      * bounced: triggered by gateway bounce (mail) or in _prepare_mass_sms_trace_values
        if sms_number_format error when sending sms (sms)
    """
    _name = 'mailing.trace'
    _description = 'Mailing Statistics'
    _rec_name = 'id'
    _order = 'scheduled DESC'

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
    message_id = fields.Char(string='Message-ID')
    medium_id = fields.Many2one(related='mass_mailing_id.medium_id')
    source_id = fields.Many2one(related='mass_mailing_id.source_id')
    # document
    model = fields.Char(string='Document model')
    res_id = fields.Integer(string='Document ID')
    # campaign / wave data
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', index=True, ondelete='cascade')
    campaign_id = fields.Many2one(
        related='mass_mailing_id.campaign_id',
        string='Campaign',
        store=True, readonly=True, index=True)
    # Bounce and tracking
    ignored = fields.Datetime(help='Date when the email has been invalidated. '
                                   'Invalid emails are blacklisted, opted-out or invalid email format')
    scheduled = fields.Datetime(help='Date when the email has been created', default=fields.Datetime.now)
    sent = fields.Datetime(help='Date when the email has been sent')
    exception = fields.Datetime(help='Date of technical error leading to the email not being sent')
    opened = fields.Datetime(help='Date when the email has been opened the first time')
    replied = fields.Datetime(help='Date when this email has been replied for the first time.')
    bounced = fields.Datetime(help='Date when this email has bounced.')
    # Link tracking
    links_click_ids = fields.One2many('link.tracker.click', 'mailing_trace_id', string='Links click')
    clicked = fields.Datetime(help='Date when customer clicked on at least one tracked link')
    # Status
    state = fields.Selection(compute="_compute_state",
                             selection=[('outgoing', 'Outgoing'),
                                        ('exception', 'Exception'),
                                        ('sent', 'Sent'),
                                        ('opened', 'Opened'),
                                        ('replied', 'Replied'),
                                        ('bounced', 'Bounced'),
                                        ('ignored', 'Ignored')], store=True)
    failure_type = fields.Selection(selection=[
        ("SMTP", "Connection failed (outgoing mail server problem)"),
        ("RECIPIENT", "Invalid email address"),
        ("BOUNCE", "Email address rejected by destination"),
        ("UNKNOWN", "Unknown error"),
    ], string='Failure type')
    state_update = fields.Datetime(compute="_compute_state", string='State Update',
                                   help='Last state update of the mail',
                                   store=True)

    @api.depends('trace_type', 'mass_mailing_id')
    def _compute_display_name(self):
        for trace in self:
            trace.display_name = '%s: %s (%s)' % (trace.trace_type, trace.mass_mailing_id.name, trace.id)

    @api.depends('sent', 'opened', 'clicked', 'replied', 'bounced', 'exception', 'ignored')
    def _compute_state(self):
        self.update({'state_update': fields.Datetime.now()})
        for stat in self:
            if stat.ignored:
                stat.state = 'ignored'
            elif stat.exception:
                stat.state = 'exception'
            elif stat.replied:
                stat.state = 'replied'
            elif stat.opened or stat.clicked:
                stat.state = 'opened'
            elif stat.bounced:
                stat.state = 'bounced'
            elif stat.sent:
                stat.state = 'sent'
            else:
                stat.state = 'outgoing'

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

    def _get_records(self, mail_mail_ids=None, mail_message_ids=None, domain=None):
        if not self.ids and mail_mail_ids:
            base_domain = [('mail_mail_id_int', 'in', mail_mail_ids)]
        elif not self.ids and mail_message_ids:
            base_domain = [('message_id', 'in', mail_message_ids)]
        else:
            base_domain = [('id', 'in', self.ids)]
        if domain:
            base_domain = ['&'] + domain + base_domain
        return self.search(base_domain)

    def set_opened(self, mail_mail_ids=None, mail_message_ids=None):
        traces = self._get_records(mail_mail_ids, mail_message_ids, [('opened', '=', False)])
        traces.write({'opened': fields.Datetime.now(), 'bounced': False})
        return traces

    def set_clicked(self, mail_mail_ids=None, mail_message_ids=None):
        traces = self._get_records(mail_mail_ids, mail_message_ids, [('clicked', '=', False)])
        traces.write({'clicked': fields.Datetime.now()})
        return traces

    def set_replied(self, mail_mail_ids=None, mail_message_ids=None):
        traces = self._get_records(mail_mail_ids, mail_message_ids, [('replied', '=', False)])
        traces.write({'replied': fields.Datetime.now()})
        return traces

    def set_bounced(self, mail_mail_ids=None, mail_message_ids=None):
        traces = self._get_records(mail_mail_ids, mail_message_ids, [('bounced', '=', False), ('opened', '=', False)])
        traces.write({'bounced': fields.Datetime.now()})
        return traces
